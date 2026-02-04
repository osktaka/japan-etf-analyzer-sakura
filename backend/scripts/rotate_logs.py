#!/usr/bin/env python3
"""Log rotation script for ETF Analyzer.

Rotates log files exceeding size threshold and cleans up old logs.
Must be run from project root directory.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from base_batch import BaseBatchScript  # noqa: E402
from src.repositories.batch_log_repository import BatchLogRepository  # noqa: E402

# Constants
LOG_DIR = "./logs"
SIZE_THRESHOLD_MB = 10
MAX_GENERATIONS = 5
RETENTION_DAYS = 90


def get_log_files(log_dir: Path) -> List[Path]:
    """Get all .log files in the log directory."""
    if not log_dir.exists():
        return []
    return sorted(log_dir.glob("*.log"))


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    return file_path.stat().st_size / (1024 * 1024)


def rotate_file(file_path: Path, dry_run: bool = False) -> List[str]:
    """Rotate a single log file.

    Returns list of actions taken/would be taken.
    """
    actions = []

    # Shift existing rotated files
    for gen in range(MAX_GENERATIONS, 0, -1):
        old_path = file_path.parent / f"{file_path.name}.{gen}"
        new_path = file_path.parent / f"{file_path.name}.{gen + 1}"

        if old_path.exists():
            if gen == MAX_GENERATIONS:
                # Delete oldest generation
                action = f"Delete: {old_path}"
                actions.append(action)
                if not dry_run:
                    old_path.unlink()
            else:
                # Rename to next generation
                action = f"Rename: {old_path} -> {new_path}"
                actions.append(action)
                if not dry_run:
                    old_path.rename(new_path)

    # Move current log to .log.1
    new_path = file_path.parent / f"{file_path.name}.1"
    action = f"Rotate: {file_path} -> {new_path}"
    actions.append(action)
    if not dry_run:
        file_path.rename(new_path)
        # Create empty new log file
        file_path.touch()

    return actions


def delete_old_files(log_dir: Path, days: int, dry_run: bool = False) -> List[str]:
    """Delete files older than specified days.

    Returns list of actions taken/would be taken.
    """
    actions = []

    # Skip if directory doesn't exist
    if not log_dir.exists():
        return actions

    cutoff_date = datetime.now() - timedelta(days=days)

    # Check all files including rotated ones
    for file_path in log_dir.iterdir():
        if not file_path.is_file():
            continue
        if file_path.name == ".gitkeep":
            continue

        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        if mtime < cutoff_date:
            action = f"Delete old file ({days}+ days): {file_path}"
            actions.append(action)
            if not dry_run:
                file_path.unlink()

    return actions


def cleanup_db_logs(days: int, dry_run: bool = False) -> str:
    """Clean up old batch logs from database.

    Returns action description.
    """
    if dry_run:
        return f"Would delete DB batch logs older than {days} days"

    try:
        repo = BatchLogRepository()
        deleted_count = repo.delete_old_logs(days=days)
        return f"Deleted {deleted_count} DB batch logs older than {days} days"
    except Exception as e:
        return f"Failed to cleanup DB logs: {e}"


class RotateLogsScript(BaseBatchScript):
    """Log rotation batch script."""

    batch_name = "rotate_logs"
    description = "Rotate log files and clean up old logs"
    enable_batch_log = True
    enable_progress = False
    enable_resume = False

    def add_custom_arguments(self, parser):
        """カスタム引数を追加"""
        parser.add_argument(
            "--size-mb",
            type=int,
            default=SIZE_THRESHOLD_MB,
            help=f"Size threshold in MB (default: {SIZE_THRESHOLD_MB})",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=RETENTION_DAYS,
            help=f"Days to retain logs (default: {RETENTION_DAYS})",
        )

    def execute(self) -> int:
        """メイン処理"""
        log_dir = Path(LOG_DIR)

        # Create logs directory if it doesn't exist
        if not log_dir.exists():
            if self.args.dry_run:
                self.logger.info(f"Would create directory: {log_dir}")
            else:
                log_dir.mkdir(parents=True)
                self.logger.info(f"Created directory: {log_dir}")

        self.logger.info(
            f"Settings: size_threshold={self.args.size_mb}MB, "
            f"retention={self.args.retention_days}days"
        )

        # バッチログ開始
        self._start_batch_log()

        try:
            all_actions = []

            # Rotate large log files
            log_files = get_log_files(log_dir)
            for log_file in log_files:
                size_mb = get_file_size_mb(log_file)
                if size_mb >= self.args.size_mb:
                    self.logger.info(
                        f"Rotating {log_file} ({size_mb:.2f}MB >= {self.args.size_mb}MB)"
                    )
                    actions = rotate_file(log_file, dry_run=self.args.dry_run)
                    all_actions.extend(actions)
                    for action in actions:
                        self.logger.info(f"  {action}")
                else:
                    self.logger.info(
                        f"Skipping {log_file} ({size_mb:.2f}MB < {self.args.size_mb}MB)"
                    )

            # Delete old files
            self.logger.info(f"Checking for files older than {self.args.retention_days} days...")
            actions = delete_old_files(
                log_dir, self.args.retention_days, dry_run=self.args.dry_run
            )
            all_actions.extend(actions)
            if actions:
                for action in actions:
                    self.logger.info(f"  {action}")
            else:
                self.logger.info("  No old files to delete")

            # Cleanup DB logs
            self.logger.info("Cleaning up database batch logs...")
            db_action = cleanup_db_logs(self.args.retention_days, dry_run=self.args.dry_run)
            self.logger.info(f"  {db_action}")

            self.logger.info(f"Log rotation completed. Total actions: {len(all_actions)}")

            # バッチログ終了（成功）
            self._finish_batch_log(success=True)
            return 0

        except Exception as e:
            # バッチログ終了（失敗）
            self._finish_batch_log(success=False, error_message=str(e))
            raise


if __name__ == "__main__":
    script = RotateLogsScript()
    sys.exit(script.run())
