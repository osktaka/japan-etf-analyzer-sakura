#!/usr/bin/env python3
"""Update ETF price data from Yahoo Finance.

Usage:
    python scripts/update_etf_data.py [--limit N] [--dry-run]

Options:
    --limit N    Only update first N ETFs (for testing)
    --dry-run    Show what would be updated without actually fetching

This script should be run via cron:
    0 19 * * 1-5 cd ~/app/backend && python3 scripts/update_etf_data.py >> ~/logs/etf_update.log 2>&1
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

ETF_MASTER_PATH = Path(__file__).parent.parent / "src" / "data" / "etf_master.json"
RATE_LIMIT_SECONDS = 1.0  # Yahoo Finance API rate limit対策


def load_etf_list() -> list:
    """Load ETF list from master JSON."""
    if not ETF_MASTER_PATH.exists():
        logger.error(f"ETF master file not found: {ETF_MASTER_PATH}")
        return []

    with open(ETF_MASTER_PATH, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("etfs", [])


def update_single_etf(code: str, dry_run: bool = False) -> bool:
    """Update price data for a single ETF.

    Args:
        code: ETF code (e.g., "1306")
        dry_run: If True, don't actually fetch data

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would update ETF {code}")
        return True

    try:
        import yfinance as yf

        ticker = f"{code}.T"
        stock = yf.Ticker(ticker)

        # 過去1年分のデータを取得
        df = stock.history(period="1y")
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return False

        # DBに保存（Flask app contextが必要）
        save_to_db(code, df)
        logger.info(f"Updated {code}: {len(df)} records")
        return True

    except Exception as e:
        logger.error(f"Failed to update {code}: {e}")
        return False


def save_to_db(code: str, df) -> None:
    """Save price data to database."""
    from src.models import PriceHistory, db

    for date, row in df.iterrows():
        date_obj = date.date() if hasattr(date, "date") else date

        existing = PriceHistory.query.filter_by(etf_code=code, date=date_obj).first()

        if existing:
            existing.open = round(float(row["Open"]), 2)
            existing.high = round(float(row["High"]), 2)
            existing.low = round(float(row["Low"]), 2)
            existing.close = round(float(row["Close"]), 2)
            existing.volume = int(row["Volume"])
            existing.updated_at = datetime.utcnow()
        else:
            record = PriceHistory(
                etf_code=code,
                date=date_obj,
                open=round(float(row["Open"]), 2),
                high=round(float(row["High"]), 2),
                low=round(float(row["Low"]), 2),
                close=round(float(row["Close"]), 2),
                volume=int(row["Volume"]),
            )
            db.session.add(record)

    db.session.commit()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update ETF price data")
    parser.add_argument("--limit", type=int, help="Limit number of ETFs to update")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be updated"
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"ETF Data Update Started at {datetime.now()}")
    logger.info("=" * 60)

    etfs = load_etf_list()
    if not etfs:
        logger.error("No ETFs found in master list")
        return 1

    if args.limit:
        etfs = etfs[: args.limit]
        logger.info(f"Limited to first {args.limit} ETFs")

    logger.info(f"Updating {len(etfs)} ETFs...")

    # Flask app contextが必要（dry-run以外）
    if not args.dry_run:
        os.environ["USE_MOCK_DATA"] = "false"
        from src.app import create_app

        app = create_app()
        ctx = app.app_context()
        ctx.push()

    success_count = 0
    fail_count = 0

    try:
        for i, etf in enumerate(etfs, 1):
            code = etf["code"]
            logger.info(f"[{i}/{len(etfs)}] Processing {code} ({etf.get('name', '')})")

            if update_single_etf(code, dry_run=args.dry_run):
                success_count += 1
            else:
                fail_count += 1

            # レート制限対策（最後の銘柄以外）
            if i < len(etfs) and not args.dry_run:
                time.sleep(RATE_LIMIT_SECONDS)

    finally:
        if not args.dry_run:
            ctx.pop()

    logger.info("=" * 60)
    logger.info(f"Update completed: {success_count} success, {fail_count} failed")
    logger.info(f"Finished at {datetime.now()}")
    logger.info("=" * 60)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
