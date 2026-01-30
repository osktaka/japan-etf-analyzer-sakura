#!/usr/bin/env python3
"""Log rotation script for ETF Analyzer.

Rotates log files exceeding size threshold and cleans up old logs.
Must be run from project root directory.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def get_rotated_files(base_path: Path) -> List[Tuple[Path, int]]:
    """Get existing rotated files with their generation numbers."""
    rotated = []
    for i in range(1, MAX_GENERATIONS + 1):
        rotated_path = base_path.parent / f"{base_path.name}.{i}"
        if rotated_path.exists():
            rotated.append((rotated_path, i))
    return rotated


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

    # Calculate paths relative to script location
    # Script: backend/scripts/rotate_logs.py → backend_dir: backend/
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent

    # Determine database path (differs between Docker and production)
    # Docker:      /app/data/etf.db (backend_dir = /app)
    # Production:  project_root/data/etf.db (backend_dir = project_root/backend)
    db_path_docker = backend_dir / "data" / "etf.db"
    db_path_prod = backend_dir.parent / "data" / "etf.db"

    # Use Docker path if it exists, otherwise production path
    db_path = db_path_docker if db_path_docker.exists() else db_path_prod
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

    try:
        from src.app import create_app
        from src.repositories.batch_log_repository import BatchLogRepository

        app = create_app()
        with app.app_context():
            repo = BatchLogRepository()
            deleted_count = repo.delete_old_logs(days=days)
            return f"Deleted {deleted_count} DB batch logs older than {days} days"
    except Exception as e:
        return f"Failed to cleanup DB logs: {e}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rotate log files and clean up old logs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
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
    args = parser.parse_args()

    log_dir = Path(LOG_DIR)

    # Create logs directory if it doesn't exist
    if not log_dir.exists():
        if args.dry_run:
            print(f"Would create directory: {log_dir}")
        else:
            log_dir.mkdir(parents=True)
            print(f"Created directory: {log_dir}")

    print(f"Log rotation started at {datetime.now().isoformat()}")
    print(f"Settings: size_threshold={args.size_mb}MB, retention={args.retention_days}days")
    if args.dry_run:
        print("** DRY RUN MODE - No changes will be made **")
    print()

    # Flask app context and batch log (non-dry-run only)
    batch_log = None
    batch_log_repo = None
    app = None
    ctx = None
    if not args.dry_run:
        # Calculate database path
        script_dir = Path(__file__).resolve().parent
        backend_dir = script_dir.parent
        db_path_docker = backend_dir / "data" / "etf.db"
        db_path_prod = backend_dir.parent / "data" / "etf.db"
        db_path = db_path_docker if db_path_docker.exists() else db_path_prod
        os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

        from src.app import create_app
        from src.repositories import BatchLogRepository

        app = create_app()
        ctx = app.app_context()
        ctx.push()

        batch_log_repo = BatchLogRepository()
        batch_log = batch_log_repo.create(
            batch_name="rotate_logs",
            status="running",
            started_at=datetime.utcnow(),
        )
        print(f"Batch log created: id={batch_log.id}\n")

    try:
        all_actions = []

        # Rotate large log files
        log_files = get_log_files(log_dir)
        for log_file in log_files:
            size_mb = get_file_size_mb(log_file)
            if size_mb >= args.size_mb:
                print(f"Rotating {log_file} ({size_mb:.2f}MB >= {args.size_mb}MB)")
                actions = rotate_file(log_file, dry_run=args.dry_run)
                all_actions.extend(actions)
                for action in actions:
                    print(f"  {action}")
            else:
                print(f"Skipping {log_file} ({size_mb:.2f}MB < {args.size_mb}MB)")

        print()

        # Delete old files
        print(f"Checking for files older than {args.retention_days} days...")
        actions = delete_old_files(log_dir, args.retention_days, dry_run=args.dry_run)
        all_actions.extend(actions)
        if actions:
            for action in actions:
                print(f"  {action}")
        else:
            print("  No old files to delete")

        print()

        # Cleanup DB logs
        print("Cleaning up database batch logs...")
        db_action = cleanup_db_logs(args.retention_days, dry_run=args.dry_run)
        print(f"  {db_action}")

        print()
        print(f"Log rotation completed. Total actions: {len(all_actions)}")

        # Update batch log to success
        if batch_log_repo and batch_log:
            batch_log_repo.update(
                batch_log.id,
                status="success",
                finished_at=datetime.utcnow(),
            )
            print(f"\nBatch log updated: id={batch_log.id}, status=success")

    except Exception as e:
        # Update batch log to failed
        if batch_log_repo and batch_log:
            batch_log_repo.update(
                batch_log.id,
                status="failed",
                finished_at=datetime.utcnow(),
                error_message=str(e),
            )
            print(f"\nBatch log updated: id={batch_log.id}, status=failed")
        raise

    finally:
        if ctx:
            ctx.pop()


if __name__ == "__main__":
    main()
