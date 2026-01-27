#!/usr/bin/env python3
"""Update ETF price data from Yahoo Finance.

Usage:
    python scripts/update_etf_data.py [--limit N] [--dry-run] [--skip-performance]

Options:
    --limit N           Only update first N ETFs (for testing)
    --dry-run           Show what would be updated without actually fetching
    --skip-performance  Skip performance cache calculation

This script should be run via cron:
    0 19 * * 1-5 cd ~/app/backend && python3 scripts/update_etf_data.py >> ~/logs/etf_update.log 2>&1
"""
import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

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

        # ticker.info から配当利回りと総資産を取得
        info = stock.info
        dividend_yield = info.get("dividendYield")  # 既にパーセント値 (e.g., 1.94)
        total_assets = info.get("totalAssets")  # 整数 (円)

        # 配当利回りを丸める
        if dividend_yield is not None:
            dividend_yield = round(dividend_yield, 2)

        # DBに保存（Flask app contextが必要）
        save_to_db(code, df)
        update_etf_info(code, dividend_yield, total_assets)
        yield_str = f"{dividend_yield}%" if dividend_yield else "N/A"
        assets_str = f"{total_assets:,}" if total_assets else "N/A"
        logger.info(
            f"Updated {code}: {len(df)} records, yield={yield_str}, assets={assets_str}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to update {code}: {e}")
        # トランザクションをロールバックして次の処理を可能にする
        try:
            from src.models import db

            db.session.rollback()
        except Exception:
            pass
        return False


def update_etf_info(
    code: str, dividend_yield: Optional[float], total_assets: Optional[int]
) -> None:
    """Update ETF info (dividend yield, total assets)."""
    from src.models import ETF, db

    etf = ETF.query.filter_by(code=code).first()
    if etf:
        if dividend_yield is not None:
            etf.dividend_yield = dividend_yield
        if total_assets is not None:
            etf.total_assets = total_assets
        db.session.commit()


def save_to_db(code: str, df) -> None:
    """Save price data to database."""
    from src.models import PriceHistory, db

    # NaN行を除去
    df_clean = df.dropna(subset=["Open", "High", "Low", "Close"])
    skipped = len(df) - len(df_clean)
    if skipped > 0:
        logger.warning(f"{code}: Skipped {skipped} rows with NaN values")

    for date, row in df_clean.iterrows():
        date_obj = date.date() if hasattr(date, "date") else date

        # 追加のNaNチェック（念のため）
        if any(math.isnan(row[col]) for col in ["Open", "High", "Low", "Close"]):
            continue

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


# 上昇率計算用の期間定義
PERIODS = {
    "1m": 30,
    "3m": 90,
    "6m": 180,
    "1y": 365,
    "3y": 1095,
    "5y": 1825,
    "10y": 3650,
    "20y": 7300,
}


def calculate_return_from_df(df, days: int) -> Optional[float]:
    """Calculate return rate from a DataFrame.

    Args:
        df: DataFrame with price data (requires 'Close' column)
        days: Number of days for the period

    Returns:
        Return percentage or None if insufficient data
    """
    if df.empty or len(df) < 2:
        return None

    # 必要な日数分のデータがあるか（80%以上で許容）
    if len(df) < days * 0.5:
        return None

    # 指定日数分の範囲を取得（最新から遡って）
    df_period = df.tail(min(days, len(df)))
    if len(df_period) < 2:
        return None

    first_close = df_period.iloc[0]["Close"]
    last_close = df_period.iloc[-1]["Close"]

    if first_close is None or last_close is None or first_close == 0:
        return None

    if math.isnan(first_close) or math.isnan(last_close):
        return None

    return round(((last_close - first_close) / first_close) * 100, 2)


def calculate_volatility_from_df(df, days: int = 365) -> Optional[float]:
    """Calculate annualized volatility from a DataFrame.

    Args:
        df: DataFrame with price data (requires 'Close' column)
        days: Number of days to analyze (default: 365 for 1 year)

    Returns:
        Annualized volatility percentage or None if insufficient data
    """
    if df.empty or len(df) < 10:
        return None

    # 指定日数分の範囲を取得（最新から遡って）
    df_period = df.tail(min(days, len(df)))
    if len(df_period) < 10:
        return None

    # 日次リターンを計算
    closes = df_period["Close"].dropna()
    if len(closes) < 10:
        return None

    daily_returns = []
    for i in range(1, len(closes)):
        prev_close = closes.iloc[i - 1]
        curr_close = closes.iloc[i]

        if prev_close and curr_close and prev_close > 0:
            if not math.isnan(prev_close) and not math.isnan(curr_close):
                daily_return = (curr_close - prev_close) / prev_close
                daily_returns.append(daily_return)

    if len(daily_returns) < 5:
        return None

    # 標準偏差を計算
    mean = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
    std_dev = math.sqrt(variance)

    # 年率化（営業日数の平方根を掛ける）
    annualized = std_dev * math.sqrt(252) * 100

    return round(annualized, 2)


def update_performance_cache(codes: list) -> tuple:
    """Update performance cache for given ETF codes.

    Args:
        codes: List of ETF codes to update

    Returns:
        Tuple of (success_count, fail_count)
    """
    import yfinance as yf
    from src.models import PerformanceCache, db

    logger.info(f"Calculating performance cache for {len(codes)} ETFs...")
    success = 0
    fail = 0

    for i, code in enumerate(codes, 1):
        try:
            ticker = f"{code}.T"
            stock = yf.Ticker(ticker)

            # 最大期間のデータを取得（20年分）
            df = stock.history(period="max")
            if df.empty:
                logger.warning(
                    f"[{i}/{len(codes)}] {code}: No data for performance calc"
                )
                fail += 1
                continue

            # ボラティリティを計算（1年データから）
            volatility = calculate_volatility_from_df(df, 365)

            # 各期間の上昇率を計算
            for period_id, days in PERIODS.items():
                return_rate = calculate_return_from_df(df, days)

                # DBに保存（UPSERT）
                existing = PerformanceCache.query.filter_by(
                    etf_code=code, period=period_id
                ).first()

                # ボラティリティは1y期間のレコードにのみ保存
                vol_value = volatility if period_id == "1y" else None

                if existing:
                    existing.return_rate = return_rate
                    existing.volatility = vol_value
                    existing.calculated_at = datetime.utcnow()
                else:
                    cache = PerformanceCache(
                        etf_code=code,
                        period=period_id,
                        return_rate=return_rate,
                        volatility=vol_value,
                        calculated_at=datetime.utcnow(),
                    )
                    db.session.add(cache)

            db.session.commit()
            success += 1
            vol_str = f"{volatility}%" if volatility else "N/A"
            logger.info(
                f"[{i}/{len(codes)}] {code}: Performance cache updated (vol={vol_str})"
            )

            # レート制限対策
            if i < len(codes):
                time.sleep(RATE_LIMIT_SECONDS)

        except Exception as e:
            logger.error(f"[{i}/{len(codes)}] {code}: Performance calc failed - {e}")
            db.session.rollback()
            fail += 1

    return success, fail


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update ETF price data")
    parser.add_argument("--limit", type=int, help="Limit number of ETFs to update")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be updated"
    )
    parser.add_argument(
        "--skip-performance",
        action="store_true",
        help="Skip performance cache calculation",
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

        # パフォーマンスキャッシュの更新
        if not args.dry_run and not args.skip_performance:
            logger.info("-" * 60)
            logger.info("Starting performance cache calculation...")
            codes = [etf["code"] for etf in etfs]
            perf_success, perf_fail = update_performance_cache(codes)
            logger.info(
                f"Performance cache: {perf_success} success, {perf_fail} failed"
            )

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
