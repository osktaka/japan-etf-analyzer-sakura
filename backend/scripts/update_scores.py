#!/usr/bin/env python3
"""Update score cache for all ETFs.

Usage:
    python scripts/update_scores.py [--limit N] [--dry-run]
    python scripts/update_scores.py --resume BATCH_LOG_ID [--dry-run]

Options:
    --limit N           Only update first N ETFs (for testing)
    --dry-run           Show what would be updated without actually saving
    --resume ID         Resume from failed batch log ID

This script should be run via cron after update_etf_data.py:
    30 19 * * 1-5 cd ~/app/backend && python3 scripts/update_scores.py >> ~/logs/score_update.log 2>&1
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env file if it exists
project_root = Path(__file__).resolve().parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import create_app  # noqa: E402
from src.repositories import (  # noqa: E402
    BatchLogRepository,
    ETFRepository,
    ScoreCacheRepository,
)
from src.services.scoring_service import ScoringService  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


PERSPECTIVES = ["dividend", "low-cost", "stability", "volume", "growth", "balance"]


def update_scores(limit: int = None, dry_run: bool = False, resume: int = None) -> dict:
    """Update score cache for all ETFs.

    Args:
        limit: Maximum number of ETFs to process
        dry_run: If True, don't save to database
        resume: Batch log ID to resume from

    Returns:
        Statistics dictionary
    """
    app = create_app()
    with app.app_context():
        etf_repo = ETFRepository()
        score_cache_repo = ScoreCacheRepository()
        scoring_service = ScoringService()

        # Get all ETFs
        all_etfs = etf_repo.search(limit=None, offset=0)
        all_etf_codes = [etf.code for etf in all_etfs]

        # ETFリストをコードでソート（再開時の一貫性確保）
        all_etfs = sorted(all_etfs, key=lambda x: x.code)

        # Batch log recording (non-dry-run only)
        batch_log = None
        batch_log_repo = None
        parent_last_item_code = None

        if not dry_run:
            batch_log_repo = BatchLogRepository()

            if resume:
                # リトライレコード作成
                batch_log = batch_log_repo.create_retry(resume)
                if not batch_log:
                    logger.error(f"Parent batch log not found: id={resume}")
                    raise ValueError(f"Parent batch log not found: id={resume}")
                parent = batch_log_repo.get_by_id(resume)
                parent_last_item_code = parent.last_item_code if parent else None
                logger.info(f"Resuming from batch log {resume}, last_item_code={parent_last_item_code}")
            else:
                # 新規バッチログ作成
                batch_log = batch_log_repo.create(
                    batch_name="update_scores",
                    status="running",
                    started_at=datetime.utcnow(),
                    total_count=len(all_etfs),
                )
                logger.info(f"Batch log created: id={batch_log.id}")

        # 処理対象のETFリストを決定
        if limit:
            etfs = all_etfs[:limit]
        else:
            etfs = all_etfs

        # 再開処理（last_item_code以降のETFのみ処理）
        if parent_last_item_code:
            resume_index = next(
                (i for i, e in enumerate(etfs) if e.code > parent_last_item_code),
                len(etfs)
            )
            etfs = etfs[resume_index:]
            logger.info(f"Resuming from index {resume_index}, {len(etfs)} ETFs remaining")

        total_etfs = len(etfs)
        logger.info(f"Processing {total_etfs} ETFs...")

        try:
            # Batch fetch data for ALL ETFs (for percentile calculation)
            logger.info("Fetching data for percentile calculation...")
            scoring_service._avg_volumes_cache = etf_repo.get_average_volumes_batch(
                all_etf_codes
            )
            scoring_service._return_rates_cache = etf_repo.get_return_rates_batch(
                all_etf_codes
            )

            # Collect percentile data from ALL ETFs
            scoring_service._collect_percentile_data(all_etfs)

            updated_count = 0
            skipped_count = 0
            processed_count = 0

            # Calculate scores for each ETF
            for idx, etf in enumerate(etfs, 1):
                logger.info(f"[{idx}/{total_etfs}] Processing {etf.code} ({etf.name})...")

                try:
                    # Calculate scores for all perspectives
                    for perspective in PERSPECTIVES:
                        # Calculate total score (partial mode - default)
                        total_score = scoring_service.calculate_score(etf, perspective, mode="partial")

                        # Calculate total score (full mode - all 5 axes)
                        total_score_full = scoring_service.calculate_score(etf, perspective, mode="full")

                        # Get individual axis scores
                        axis_scores = {}
                        weights = scoring_service.WEIGHTS[perspective]
                        for axis in weights.keys():
                            axis_score = scoring_service._get_axis_score(etf, axis)
                            # Convert to 0-100 scale (same as total_score)
                            if axis_score is not None:
                                axis_scores[axis] = round(axis_score * 100, 1)
                            else:
                                axis_scores[axis] = None

                        if not dry_run:
                            # Save to cache
                            score_cache_repo.upsert(
                                etf_code=etf.code,
                                perspective=perspective,
                                total_score=round(total_score, 1),
                                total_score_full=round(total_score_full, 1),
                                axis_scores=axis_scores,
                            )
                        else:
                            logger.info(
                                f"  {perspective}: partial={total_score:.1f}, full={total_score_full:.1f} (dry-run)"
                            )

                    updated_count += 1
                    processed_count += 1

                    # 10件ごとに進捗更新
                    if not dry_run and batch_log and processed_count % 10 == 0:
                        batch_log_repo.update_progress(
                            batch_log.id,
                            processed_count=processed_count,
                            last_item_code=etf.code,
                        )
                        logger.info(f"Progress updated: {processed_count} processed")

                except Exception as e:
                    logger.error(f"Error processing {etf.code}: {e}")
                    skipped_count += 1
                    continue

            # 最終進捗更新
            if not dry_run and batch_log and processed_count % 10 != 0:
                batch_log_repo.update_progress(
                    batch_log.id,
                    processed_count=processed_count,
                    last_item_code=etfs[-1].code if etfs else None,
                )

            # Update batch log to success
            if batch_log_repo and batch_log:
                batch_log_repo.update(
                    batch_log.id,
                    status="success",
                    finished_at=datetime.utcnow(),
                )
                logger.info(f"Batch log updated: id={batch_log.id}, status=success")

        except Exception as e:
            # Update batch log to failed
            if batch_log_repo and batch_log:
                batch_log_repo.update(
                    batch_log.id,
                    status="failed",
                    finished_at=datetime.utcnow(),
                    error_message=str(e),
                )
                logger.error(f"Batch log updated: id={batch_log.id}, status=failed")
            raise

        finally:
            # Clear cache
            scoring_service._avg_volumes_cache = {}
            scoring_service._return_rates_cache = {}

        stats = {
            "total_etfs": total_etfs,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "dry_run": dry_run,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Completed: {updated_count} updated, {skipped_count} skipped")
        return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update score cache for all ETFs")
    parser.add_argument("--limit", type=int, help="Only update first N ETFs")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without actually saving",
    )
    parser.add_argument(
        "--resume",
        type=int,
        help="Resume from failed batch log ID",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Score Cache Update Started")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be saved")

    try:
        stats = update_scores(limit=args.limit, dry_run=args.dry_run, resume=args.resume)
        logger.info("=" * 60)
        logger.info("Score Cache Update Completed Successfully")
        logger.info(f"Total ETFs: {stats['total_etfs']}")
        logger.info(f"Updated: {stats['updated_count']}")
        logger.info(f"Skipped: {stats['skipped_count']}")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
