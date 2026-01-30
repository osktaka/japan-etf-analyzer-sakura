#!/usr/bin/env python3
"""Update ETF price data from Yahoo Finance.

Usage:
    python scripts/update_etf_data.py [--limit N] [--dry-run] [--skip-performance] [--rate-limit N]
    python scripts/update_etf_data.py --smart [--limit N] [--dry-run] [--rate-limit N]

Options:
    --limit N           Only update first N ETFs (for testing)
    --dry-run           Show what would be updated without actually fetching
    --skip-performance  Skip performance cache calculation
    --full              Fetch full history (period='max') instead of 1 year
    --smart             Smart update: full history for new ETFs, incremental for existing
    --rate-limit N      Rate limit in seconds between requests (default: 1.0)

This script should be run via cron:
    0 19 * * 1-5 cd ~/app/backend && python3 scripts/update_etf_data.py --smart --rate-limit 3.0 >> ~/logs/etf_update.log 2>&1
"""
import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

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

# Yahoo Finance API 429エラー対策: User-Agentをブラウザのものに設定
import requests
_original_request = requests.Session.request
def _custom_request(self, method, url, **kwargs):
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
    if 'User-Agent' not in kwargs['headers']:
        kwargs['headers']['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    return _original_request(self, method, url, **kwargs)
requests.Session.request = _custom_request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("yfinance").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ETF_MASTER_PATH = Path(__file__).parent.parent / "src" / "data" / "etf_master.json"
RATE_LIMIT_SECONDS = 1.0  # Yahoo Finance API rate limit対策
JST = timezone(timedelta(hours=9))  # Japan Standard Time


def get_etf_price_status(code: str) -> Tuple[bool, Optional[datetime], Optional[datetime]]:
    """Check if ETF has existing price data and get the latest date and update time.

    Args:
        code: ETF code (e.g., "1306")

    Returns:
        Tuple of (has_data, latest_date, updated_at)
        - has_data: True if ETF has any price history
        - latest_date: The most recent date in price history, or None if no data
        - updated_at: The updated_at timestamp of the latest record, or None if no data
    """
    from sqlalchemy import func

    from src.models import PriceHistory

    latest_record = (
        PriceHistory.query.filter_by(etf_code=code)
        .order_by(PriceHistory.date.desc())
        .first()
    )
    if latest_record:
        return (True, latest_record.date, latest_record.updated_at)
    return (False, None, None)


def load_etf_list() -> list:
    """Load ETF list from master JSON."""
    if not ETF_MASTER_PATH.exists():
        logger.error(f"ETF master file not found: {ETF_MASTER_PATH}")
        return []

    with open(ETF_MASTER_PATH, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("etfs", [])


def update_single_etf(
    code: str,
    dry_run: bool = False,
    full: bool = False,
    smart: bool = False,
) -> bool:
    """Update price data for a single ETF.

    Args:
        code: ETF code (e.g., "1306")
        dry_run: If True, don't actually fetch data
        full: If True, fetch full history (period='max') instead of 1 year
        smart: If True, use smart update (full for new, incremental for existing)

    Returns:
        True if successful, False otherwise
    """
    # Smart mode: check existing data status (store result for later use)
    smart_status = None
    if smart and not dry_run:
        smart_status = get_etf_price_status(code)
        has_data, latest_date, updated_at = smart_status
        if not has_data:
            logger.info(f"[SMART] {code}: New ETF - fetching full history")
            full = True
        else:
            logger.info(
                f"[SMART] {code}: Existing ETF - incremental from {latest_date}"
            )
    elif smart and dry_run:
        # In dry-run mode, we can still check status for logging
        logger.info(f"[DRY-RUN][SMART] Would check status and update ETF {code}")
        return True

    if dry_run:
        mode = "full history" if full else "1 year"
        logger.info(f"[DRY-RUN] Would update ETF {code} ({mode})")
        return True

    try:
        import yfinance as yf

        ticker = f"{code}.T"
        stock = yf.Ticker(ticker)

        # Smart mode with existing data: use start date for incremental fetch
        if smart and not full and smart_status:
            has_data, latest_date, updated_at = smart_status
            if has_data and latest_date:
                # Check if re-fetch is needed based on cutoff time (15:30 JST)
                now_jst = datetime.now(JST)
                today_jst = now_jst.date()
                cutoff_time = time(15, 30)

                # Convert updated_at (UTC) to JST for comparison
                if updated_at:
                    updated_at_jst = updated_at.replace(tzinfo=timezone.utc).astimezone(JST)
                    updated_time_jst = updated_at_jst.time()
                else:
                    updated_time_jst = None

                if latest_date == today_jst and updated_time_jst and updated_time_jst < cutoff_time:
                    # Today's data updated before 15:30 JST - re-fetch from latest date
                    start_date = latest_date
                    logger.info(f"[SMART] {code}: Re-fetching today's data (updated at {updated_at_jst.strftime('%H:%M:%S')} JST)")
                else:
                    # Either not today, or already updated after 15:30 - fetch next day onwards
                    start_date = latest_date + timedelta(days=1)
                df = stock.history(start=start_date.strftime("%Y-%m-%d"))
                if df.empty:
                    logger.info(f"{code}: No new data since {latest_date}")
                    # Still update ETF info even if no new price data
                    info = stock.info
                    dividend_yield = info.get("dividendYield")
                    total_assets = info.get("totalAssets")
                    if dividend_yield is not None:
                        dividend_yield = round(dividend_yield, 2)
                    market_price = info.get("regularMarketPrice")
                    if market_price is not None:
                        market_price = round(float(market_price), 2)
                    update_etf_info(code, dividend_yield, total_assets, market_price)
                    return True
            else:
                # Fallback to full if status check failed
                full = True

        # Regular fetch (full or 1y period)
        if not smart or full:
            period = "max" if full else "1y"
            df = stock.history(period=period)
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

        # 株式分割検知処理（データが2行以上ある場合のみ）
        if not df.empty and len(df) >= 2:
            check_stock_split(code, df)

        # DBに保存（Flask app contextが必要）
        save_to_db(code, df)
        market_price = round(float(df["Close"].iloc[-1]), 2) if not df.empty else None
        update_etf_info(code, dividend_yield, total_assets, market_price)
        yield_str = f"{dividend_yield}%" if dividend_yield else "N/A"
        assets_str = f"{total_assets:,}" if total_assets else "N/A"
        mode_str = "[FULL]" if full else ("[INCR]" if smart else "")
        logger.info(
            f"Updated {code} {mode_str}: {len(df)} records, yield={yield_str}, assets={assets_str}"
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
    code: str,
    dividend_yield: Optional[float],
    total_assets: Optional[int],
    market_price: Optional[float] = None,
) -> None:
    """Update ETF info (dividend yield, total assets, market price)."""
    from src.models import ETF, db

    etf = ETF.query.filter_by(code=code).first()
    if etf:
        if dividend_yield is not None:
            etf.dividend_yield = dividend_yield
        if total_assets is not None:
            etf.total_assets = total_assets
        if market_price is not None:
            etf.market_price = market_price
        db.session.commit()


def check_stock_split(code: str, df) -> None:
    """Check for stock splits based on price changes.

    Args:
        code: ETF code
        df: DataFrame with price data (requires 'Close' column and date index)
    """
    try:
        from src.services.split_detection_service import SplitDetectionService

        # 最新2日分のデータを取得
        if len(df) < 2:
            return

        # 前日と当日の終値を取得
        previous_close = float(df["Close"].iloc[-2])
        current_close = float(df["Close"].iloc[-1])
        current_date = df.index[-1].date()

        # 分割検知サービスを使用
        split_service = SplitDetectionService()
        stock_split = split_service.check_for_splits(
            etf_code=code,
            previous_close=previous_close,
            current_close=current_close,
            current_date=current_date,
        )

        # 検知された分割をDBに登録
        if stock_split:
            split_service.register_split(stock_split)

    except Exception as e:
        # 分割検知の失敗は全体の処理を止めない
        logger.warning(f"{code}: Stock split check failed - {e}")


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


def calculate_regression_return_from_df(df, days: int) -> Optional[float]:
    """Calculate regression-based return rate from a DataFrame.

    Uses least squares method to fit a linear regression line (y = ax + b)
    and calculates the return based on the regression line endpoints.

    Args:
        df: DataFrame with price data (requires 'Close' column)
        days: Number of days for the period

    Returns:
        Regression return percentage or None if insufficient data
    """
    if df.empty or len(df) < 2:
        return None

    # 必要な日数分のデータがあるか（50%以上で許容）
    if len(df) < days * 0.5:
        return None

    # 指定日数分の範囲を取得（最新から遡って）
    df_period = df.tail(min(days, len(df)))
    if len(df_period) < 2:
        return None

    # 終値を抽出
    closes = df_period["Close"].dropna()
    prices = []
    for close in closes:
        if close is not None and not math.isnan(close):
            prices.append(close)

    if len(prices) < 2:
        return None

    n = len(prices)
    # x values: 0, 1, 2, ..., n-1
    # Least squares: y = ax + b
    # a = (n * sum(xy) - sum(x) * sum(y)) / (n * sum(x^2) - sum(x)^2)
    # b = (sum(y) - a * sum(x)) / n

    sum_x = sum(range(n))  # 0 + 1 + ... + (n-1) = n*(n-1)/2
    sum_y = sum(prices)
    sum_xy = sum(i * prices[i] for i in range(n))
    sum_x2 = sum(i * i for i in range(n))  # 0^2 + 1^2 + ... + (n-1)^2

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return None

    a = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - a * sum_x) / n

    # Regression line: start at x=0, end at x=n-1
    start_value = b  # y = a*0 + b = b
    end_value = a * (n - 1) + b  # y = a*(n-1) + b

    if start_value == 0:
        return None

    return round(((end_value - start_value) / start_value) * 100, 2)


def update_performance_cache(codes: list, rate_limit: float = 1.0) -> tuple:
    """Update performance cache for given ETF codes.

    Args:
        codes: List of ETF codes to update
        rate_limit: Rate limit in seconds between requests

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

            # 各期間の上昇率と回帰上昇率を計算
            for period_id, days in PERIODS.items():
                return_rate = calculate_return_from_df(df, days)
                regression_rate = calculate_regression_return_from_df(df, days)

                # DBに保存（UPSERT）
                existing = PerformanceCache.query.filter_by(
                    etf_code=code, period=period_id
                ).first()

                # ボラティリティは1y期間のレコードにのみ保存
                vol_value = volatility if period_id == "1y" else None

                if existing:
                    existing.return_rate = return_rate
                    existing.regression_rate = regression_rate
                    existing.volatility = vol_value
                    existing.calculated_at = datetime.utcnow()
                else:
                    cache = PerformanceCache(
                        etf_code=code,
                        period=period_id,
                        return_rate=return_rate,
                        regression_rate=regression_rate,
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
                time.sleep(rate_limit)

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
    parser.add_argument(
        "--full",
        action="store_true",
        help="Fetch full history (period='max') instead of 1 year",
    )
    parser.add_argument(
        "--smart",
        action="store_true",
        help="Smart update: full history for new ETFs, incremental for existing",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Rate limit in seconds between requests (default: 1.0)",
    )
    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.full and args.smart:
        logger.warning(
            "--full and --smart are mutually exclusive. --smart takes precedence."
        )
        args.full = False

    logger.info("=" * 60)
    logger.info(f"ETF Data Update Started at {datetime.now()}")
    mode_info = []
    if args.smart:
        mode_info.append("smart")
    elif args.full:
        mode_info.append("full")
    if args.dry_run:
        mode_info.append("dry-run")
    if args.skip_performance:
        mode_info.append("skip-performance")
    if mode_info:
        logger.info(f"Mode: {', '.join(mode_info)}")
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

    # バッチログ記録（dry-run以外）
    batch_log = None
    batch_log_repo = None
    if not args.dry_run:
        from src.repositories import BatchLogRepository

        batch_log_repo = BatchLogRepository()
        batch_log = batch_log_repo.create(
            batch_name="update_etf_data",
            status="running",
            started_at=datetime.utcnow(),
        )
        logger.info(f"Batch log created: id={batch_log.id}")

    try:
        for i, etf in enumerate(etfs, 1):
            code = etf["code"]
            logger.info(f"[{i}/{len(etfs)}] Processing {code} ({etf.get('name', '')})")

            if update_single_etf(
                code, dry_run=args.dry_run, full=args.full, smart=args.smart
            ):
                success_count += 1
            else:
                fail_count += 1

            # レート制限対策（最後の銘柄以外）
            if i < len(etfs) and not args.dry_run:
                time.sleep(args.rate_limit)

        # パフォーマンスキャッシュの更新
        if not args.dry_run and not args.skip_performance:
            logger.info("-" * 60)
            logger.info("Starting performance cache calculation...")
            codes = [etf["code"] for etf in etfs]
            perf_success, perf_fail = update_performance_cache(codes, args.rate_limit)
            logger.info(
                f"Performance cache: {perf_success} success, {perf_fail} failed"
            )

        # バッチログを成功で更新
        if batch_log_repo and batch_log:
            batch_log_repo.update(
                batch_log.id,
                status="success",
                finished_at=datetime.utcnow(),
            )
            logger.info(f"Batch log updated: id={batch_log.id}, status=success")

    except Exception as e:
        # バッチログを失敗で更新
        if batch_log_repo and batch_log:
            batch_log_repo.update(
                batch_log.id,
                status="failed",
                finished_at=datetime.utcnow(),
                error_message=str(e),
            )
            logger.info(f"Batch log updated: id={batch_log.id}, status=failed")
        raise

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
