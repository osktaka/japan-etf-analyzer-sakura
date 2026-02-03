#!/usr/bin/env python3
"""
Batch Monitor Script

バッチ処理の監視とリトライを自動実行するスクリプト。
cronで10分間隔で実行することを想定（*/10 * * * *）。

処理内容:
1. 30分以上ハートビート更新がないrunningジョブをfailedに更新
2. 直近10-20分でfailedになったレコードを取得
3. retry_count < 3 のジョブを自動リトライ
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# USE_MOCK_DATAをfalseに設定（本番DB使用）
os.environ["USE_MOCK_DATA"] = "false"

from src.app import create_app
from src.repositories import BatchLogRepository


# バッチ名とスクリプトパスのマッピング
BATCH_SCRIPTS = {
    "update_etf_data": "backend/scripts/update_etf_data.py",
    "update_scores": "backend/scripts/update_scores.py",
    "sync_etf_from_jpx": "backend/scripts/sync_etf_from_jpx.py",
}


def mark_timed_out_jobs_as_failed(repo: BatchLogRepository) -> int:
    """
    30分以上ハートビート更新がないrunningジョブをfailedに更新する.

    Args:
        repo: BatchLogRepository instance

    Returns:
        更新したジョブの数
    """
    timed_out_jobs = repo.get_timed_out_jobs()
    updated_count = 0

    for job in timed_out_jobs:
        logger.warning(
            f"Timeout detected: batch_log_id={job.id}, "
            f"batch_name={job.batch_name}, "
            f"last_heartbeat={job.last_heartbeat}"
        )

        repo.update(
            job.id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message="Timed out (no heartbeat for 30+ minutes)",
        )
        updated_count += 1
        logger.info(f"Marked as failed: batch_log_id={job.id}")

    return updated_count


def retry_failed_jobs(repo: BatchLogRepository) -> int:
    """
    直近10-20分でfailedになったジョブをリトライする.

    Args:
        repo: BatchLogRepository instance

    Returns:
        リトライしたジョブの数
    """
    retryable_jobs = repo.get_retryable_jobs()
    retry_count = 0

    for job in retryable_jobs:
        # リトライ上限チェック
        if job.retry_count >= 3:
            logger.info(
                f"Skip (retry limit exceeded): batch_log_id={job.id}, "
                f"batch_name={job.batch_name}, retry_count={job.retry_count}"
            )
            continue

        # バッチスクリプトのパス取得
        script_path = BATCH_SCRIPTS.get(job.batch_name)
        if not script_path:
            logger.warning(
                f"Unknown batch name: batch_log_id={job.id}, "
                f"batch_name={job.batch_name}"
            )
            continue

        # スクリプトの存在確認
        full_script_path = project_root / script_path
        if not full_script_path.exists():
            logger.error(f"Script not found: {full_script_path}")
            continue

        # リトライ実行
        logger.info(
            f"Retrying: batch_log_id={job.id}, "
            f"batch_name={job.batch_name}, retry_count={job.retry_count}"
        )

        try:
            # バックグラウンドでスクリプト実行（nohup使用）
            cmd = [
                "nohup",
                sys.executable,
                str(full_script_path),
                "--resume",
                str(job.id),
            ]

            # バッチ固有のオプション追加
            if job.batch_name == "update_etf_data":
                cmd.extend(["--smart", "--rate-limit", "3.0"])

            # ログファイルパス
            log_dir = project_root / "backend" / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"{job.batch_name}_retry_{job.id}.log"

            # バックグラウンド実行（stdout/stderrをログファイルにリダイレクト）
            with open(log_file, "w") as f:
                subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(project_root),
                    start_new_session=True,
                )

            retry_count += 1
            logger.info(
                f"Retry started: batch_log_id={job.id}, log_file={log_file}"
            )

        except Exception as e:
            logger.error(
                f"Failed to retry: batch_log_id={job.id}, error={str(e)}"
            )

    return retry_count


def main() -> int:
    """Main entry point."""
    logger.info("=" * 60)
    logger.info(f"Batch Monitor Started at {datetime.now()}")
    logger.info("=" * 60)

    try:
        # Flask app context作成
        app = create_app()
        with app.app_context():
            repo = BatchLogRepository()

            # Step 1: タイムアウトジョブを失敗に更新
            logger.info("Checking for timed out jobs...")
            timed_out_count = mark_timed_out_jobs_as_failed(repo)
            logger.info(f"Marked {timed_out_count} timed out jobs as failed")

            # Step 2: 失敗ジョブをリトライ
            logger.info("Checking for retryable jobs...")
            retry_count = retry_failed_jobs(repo)
            logger.info(f"Retried {retry_count} failed jobs")

        logger.info("=" * 60)
        logger.info(f"Batch Monitor Completed at {datetime.now()}")
        logger.info(f"Summary: {timed_out_count} timed out, {retry_count} retried")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.exception("Unexpected error in batch monitor")
        return 1


if __name__ == "__main__":
    sys.exit(main())
