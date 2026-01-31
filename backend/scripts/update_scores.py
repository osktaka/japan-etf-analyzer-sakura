#!/usr/bin/env python3
"""Update score cache for all ETFs.

Usage:
    python scripts/update_scores.py [--limit N] [--dry-run]

Options:
    --limit N           Only update first N ETFs (for testing)
    --dry-run           Show what would be updated without actually saving

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


def update_scores(limit: int = None, dry_run: bool = False) -> dict:
    """Update score cache for all ETFs.

    Args:
        limit: Maximum number of ETFs to process
        dry_run: If True, don't save to database

    Returns:
        Statistics dictionary
    """
    app = create_app()
    with app.app_context():
        etf_repo = ETFRepository()
        score_cache_repo = ScoreCacheRepository()
        scoring_service = ScoringService()

        # Get all ETFs
        etfs = etf_repo.search(limit=limit, offset=0)
        total_etfs = len(etfs)
        logger.info(f"Processing {total_etfs} ETFs...")

        # Get all ETF codes for percentile calculation
        all_etfs = etf_repo.search(limit=None, offset=0)
        all_etf_codes = [etf.code for etf in all_etfs]

        # Batch log recording (non-dry-run only)
        batch_log = None
        batch_log_repo = None
        if not dry_run:
            batch_log_repo = BatchLogRepository()
            batch_log = batch_log_repo.create(
                batch_name="update_scores",
                status="running",
                started_at=datetime.utcnow(),
            )
            logger.info(f"Batch log created: id={batch_log.id}")

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

            # Calculate scores for each ETF
            for idx, etf in enumerate(etfs, 1):
                logger.info(f"[{idx}/{total_etfs}] Processing {etf.code} ({etf.name})...")

                try:
                    # Calculate scores for all perspectives
                    for perspective in PERSPECTIVES:
                        # Calculate total score
                        total_score = scoring_service.calculate_score(etf, perspective)

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
                                axis_scores=axis_scores,
                            )
                        else:
                            logger.info(
                                f"  {perspective}: {total_score:.1f} (dry-run, not saved)"
                            )

                    updated_count += 1

                except Exception as e:
                    logger.error(f"Error processing {etf.code}: {e}")
                    skipped_count += 1
                    continue

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

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Score Cache Update Started")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be saved")

    try:
        stats = update_scores(limit=args.limit, dry_run=args.dry_run)
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
