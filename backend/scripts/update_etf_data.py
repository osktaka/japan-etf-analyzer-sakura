#!/usr/bin/env python3
"""Update ETF price data from Yahoo Finance.

Usage:
    python scripts/update_etf_data.py [--limit N] [--dry-run] [--skip-performance] [--rate-limit N]
    python scripts/update_etf_data.py --smart [--limit N] [--dry-run] [--rate-limit N]
    python scripts/update_etf_data.py --resume BATCH_LOG_ID [--dry-run] [--rate-limit N]

Options:
    --limit N           Only update first N ETFs (for testing)
    --dry-run           Show what would be updated without actually fetching
    --skip-performance  Skip performance cache calculation
    --full              Fetch full history (period='max') instead of 1 year
    --smart             Smart update: full history for new ETFs, incremental for existing
    --rate-limit N      Rate limit in seconds between requests (default: 1.0)
    --resume ID         Resume from failed batch log ID

This script should be run via cron:
    0 19 * * 1-5 cd ~/app/backend && python3 scripts/update_etf_data.py --smart --rate-limit 3.0 >> ~/logs/etf_update.log 2>&1
"""
import logging
import math
import sys
import time as time_module
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Yahoo Finance API 429エラー対策: User-Agentを強制的に上書き
# yfinance 0.1.63が設定する古いUser-Agent (Chrome 39, 2014年) をブロック回避のため置換
import requests

original_prepare_request = requests.Session.prepare_request


def custom_prepare_request(self, request):
    # 常に新しいUser-Agentに置き換える（yfinanceの古いUser-Agentを上書き）
    request.headers[
        "User-Agent"
    ] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    return original_prepare_request(self, request)


requests.Session.prepare_request = custom_prepare_request

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from base_batch import BaseBatchScript  # noqa: E402

logging.getLogger("yfinance").setLevel(logging.WARNING)

# save_to_db / check_and_register_split は logger を引数で受け取らないため、
# モジュールスコープの logger が必要（未定義だと警告出力時に NameError になる）
logger = logging.getLogger(__name__)

RATE_LIMIT_SECONDS = 1.0  # Yahoo Finance API rate limit対策
JST = timezone(timedelta(hours=9))  # Japan Standard Time
MARKET_DATA_AVAILABLE_TIME = time(16, 0)  # 16:00 JST（yfinance遅延考慮）


def is_market_open_day(date) -> bool:
    """指定日が営業日（平日かつ非祝日）かどうか"""
    import jpholiday

    if date.weekday() >= 5:  # 土日
        return False
    if jpholiday.is_holiday(date):  # 日本の祝日
        return False
    return True


def get_previous_market_day(date):
    """前営業日を取得"""
    prev_day = date - timedelta(days=1)
    while not is_market_open_day(prev_day):
        prev_day -= timedelta(days=1)
    return prev_day


def get_next_market_day(date):
    """次の営業日を取得"""
    next_day = date + timedelta(days=1)
    while not is_market_open_day(next_day):
        next_day += timedelta(days=1)
    return next_day


def should_skip_fetch(latest_date, updated_at) -> Tuple[bool, str]:
    """リクエスト前に完全スキップすべきか判定

    Returns:
        (should_skip, reason)
    """
    now_jst = datetime.now(JST)
    today_jst = now_jst.date()

    # Case 1: 最新データが今日で、16:00以降に更新済み
    if latest_date == today_jst and updated_at:
        updated_at_jst = updated_at.replace(tzinfo=timezone.utc).astimezone(JST)
        if updated_at_jst.time() >= MARKET_DATA_AVAILABLE_TIME:
            next_market_day = get_next_market_day(today_jst)
            return (
                True,
                f"Today's data fetched after 16:00, next market day: {next_market_day}",
            )

    # Case 2: 今日が非営業日で、直前営業日のデータを取得済み
    if not is_market_open_day(today_jst):
        prev_market_day = get_previous_market_day(today_jst)
        if latest_date >= prev_market_day:
            return True, f"Non-market day, data up to {latest_date}"

    return False, ""


def get_etf_price_status(
    code: str
) -> Tuple[bool, Optional[datetime], Optional[datetime]]:
    """Check if ETF has existing price data and get the latest date and update time.

    Args:
        code: ETF code (e.g., "1306")

    Returns:
        Tuple of (has_data, latest_date, updated_at)
        - has_data: True if ETF has any price history
        - latest_date: The most recent date in price history, or None if no data
        - updated_at: The updated_at timestamp of the latest record, or None if no data
    """

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
    """Load ETF list from database."""
    from src.repositories import ETFRepository

    etf_repo = ETFRepository()
    etfs = etf_repo.get_all()
    return [{"code": e.code, "name": e.name} for e in etfs]


def update_single_etf(
    code: str,
    logger,
    dry_run: bool = False,
    full: bool = False,
    smart: bool = False,
) -> str:
    """Update price data for a single ETF.

    Args:
        code: ETF code (e.g., "1306")
        logger: Logger instance
        dry_run: If True, don't actually fetch data
        full: If True, fetch full history (period='max') instead of 1 year
        smart: If True, use smart update (full for new, incremental for existing)

    Returns:
        "success" if data was fetched and saved,
        "skipped" if no yfinance request was made (pre-check skip or dry-run),
        "failed" if an error occurred during fetch/save.
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
            # 事前スキップ判定（完全スキップ - yfinanceリクエストなし）
            should_skip, skip_reason = should_skip_fetch(latest_date, updated_at)
            if should_skip:
                logger.info(f"{code}: Skip (pre-check) - {skip_reason}")
                return "skipped"

            logger.info(
                f"[SMART] {code}: Existing ETF - incremental from {latest_date}"
            )
    elif smart and dry_run:
        # In dry-run mode, we can still check status for logging
        logger.info(f"[DRY-RUN][SMART] Would check status and update ETF {code}")
        return "skipped"

    if dry_run:
        mode = "full history" if full else "1 year"
        logger.info(f"[DRY-RUN] Would update ETF {code} ({mode})")
        return "skipped"

    try:
        import yfinance as yf

        ticker = f"{code}.T"
        stock = yf.Ticker(ticker)

        # Smart mode with existing data: use start date for incremental fetch
        if smart and not full and smart_status:
            has_data, latest_date, updated_at = smart_status
            if has_data and latest_date:
                # Check if re-fetch is needed based on cutoff time (16:00 JST)
                now_jst = datetime.now(JST)
                today_jst = now_jst.date()
                cutoff_time = time(16, 0)  # 16:00 JST（yfinance遅延考慮）

                # Convert updated_at (UTC) to JST for comparison
                if updated_at:
                    updated_at_jst = updated_at.replace(tzinfo=timezone.utc).astimezone(
                        JST
                    )
                    updated_time_jst = updated_at_jst.time()
                else:
                    updated_time_jst = None

                if (
                    latest_date == today_jst
                    and updated_time_jst
                    and updated_time_jst < cutoff_time
                ):
                    # Today's data updated before 16:00 JST - re-fetch from latest date
                    start_date = latest_date
                    logger.info(
                        f"[SMART] {code}: Re-fetching today's data (updated at {updated_at_jst.strftime('%H:%M:%S')} JST)"
                    )
                else:
                    # Either not today, or already updated after 16:00 - fetch next day onwards
                    start_date = latest_date + timedelta(days=1)
                df = stock.history(start=start_date.strftime("%Y-%m-%d"))
                if df.empty:
                    logger.info(f"{code}: No new data since {latest_date}")
                    # Still update ETF info even if no new price data
                    info = stock.info
                    market_price = info.get("regularMarketPrice")
                    if market_price is not None:
                        market_price = round(float(market_price), 2)
                    update_etf_info(code, None, None, market_price)
                    return "success"
            else:
                # Fallback to full if status check failed
                full = True

        # Regular fetch (full or 1y period)
        if not smart or full:
            period = "max" if full else "1y"
            df = stock.history(period=period)
            if df.empty:
                logger.warning(f"No data returned for {ticker}")
                return "failed"

        # 配当利回り・純資産額はsync_from_minkabu.pyで別途取得

        # 株式分割検知処理（データが2行以上ある場合のみ）
        if not df.empty and len(df) >= 2:
            check_stock_split(code, df)

        # DBに保存（Flask app contextが必要）
        save_to_db(code, df)
        market_price = round(float(df["Close"].iloc[-1]), 2) if not df.empty else None
        update_etf_info(code, None, None, market_price)
        mode_str = "[FULL]" if full else ("[INCR]" if smart else "")
        logger.info(f"Updated {code} {mode_str}: {len(df)} records")
        return "success"

    except Exception as e:
        logger.error(f"Failed to update {code}: {e}")
        # トランザクションをロールバックして次の処理を可能にする
        try:
            from src.models import db

            db.session.rollback()
        except Exception:
            pass
        return "failed"


def update_etf_info(
    code: str,
    dividend_yield: Optional[float],
    total_assets: Optional[int],
    market_price: Optional[float] = None,
) -> None:
    """Update ETF info (dividend yield, total assets, market price)."""
    from sqlalchemy import func

    from src.models import ETF, db
    from src.models.price_history import PriceHistory

    etf = ETF.query.filter_by(code=code).first()
    if etf:
        if dividend_yield is not None:
            etf.dividend_yield = dividend_yield
        if total_assets is not None:
            etf.total_assets = total_assets
        if market_price is not None:
            etf.market_price = market_price

        # listing_dateがNULLの場合、PriceHistoryの最古日付で補完
        if etf.listing_date is None:
            oldest = (
                db.session.query(func.min(PriceHistory.date))
                .filter(PriceHistory.etf_code == code)
                .scalar()
            )
            if oldest is not None:
                etf.listing_date = oldest

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


def update_performance_cache(codes: list, logger, rate_limit: float = 1.0) -> tuple:
    """Update performance cache for given ETF codes using DB-first approach.

    Args:
        codes: List of ETF codes to update
        logger: Logger instance
        rate_limit: Rate limit (deprecated - kept for backward compatibility)

    Returns:
        Tuple of (success_count, fail_count)
    """
    from src.services.performance_cache_service import PerformanceCacheService

    logger.info(f"Calculating performance cache for {len(codes)} ETFs...")
    success = 0
    fail = 0

    service = PerformanceCacheService()

    for i, code in enumerate(codes, 1):
        try:
            result = service.recalculate_for_etf(code)
            if result is None:
                logger.warning(
                    f"[{i}/{len(codes)}] {code}: No data for performance calc"
                )
                fail += 1
                continue

            success += 1
            updated_periods = ", ".join(result["updated_periods"])
            logger.info(
                f"[{i}/{len(codes)}] {code}: Performance cache updated "
                f"(periods: {updated_periods})"
            )

        except Exception as e:
            logger.error(f"[{i}/{len(codes)}] {code}: Performance calc failed - {e}")
            fail += 1

    return success, fail


def update_momentum_labels(codes, logger):
    """モメンタムラベルを更新"""
    from src.models.performance_cache import PerformanceCache
    from src.models.etf import ETF
    from src.models import db
    from src.utils.momentum import get_momentum_label

    logger.info("モメンタムラベルを更新中...")
    updated = 0

    for code in codes:
        cache_1m = PerformanceCache.query.filter_by(etf_code=code, period="1m").first()
        cache_3m = PerformanceCache.query.filter_by(etf_code=code, period="3m").first()

        rate_1m = cache_1m.regression_rate if cache_1m else None
        rate_3m = cache_3m.regression_rate if cache_3m else None

        label = get_momentum_label(rate_1m, rate_3m)

        etf = ETF.query.get(code)
        if etf and etf.momentum_label != label:
            etf.momentum_label = label
            updated += 1

    db.session.commit()
    logger.info(f"モメンタムラベル更新完了: {updated}/{len(codes)}件")


class UpdateEtfDataScript(BaseBatchScript):
    """ETF price data update batch script."""

    batch_name = "update_etf_data"
    description = "Update ETF price data from Yahoo Finance"
    enable_batch_log = True
    enable_progress = True
    enable_resume = True
    progress_interval = 10

    def add_custom_arguments(self, parser):
        """カスタム引数を追加"""
        parser.add_argument("--limit", type=int, help="Limit number of ETFs to update")
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

    def execute(self) -> int:
        """メイン処理"""
        # Validate mutually exclusive options
        if self.args.full and self.args.smart:
            self.logger.warning(
                "--full and --smart are mutually exclusive. --smart takes precedence."
            )
            self.args.full = False

        # Mode info
        mode_info = []
        if self.args.smart:
            mode_info.append("smart")
        elif self.args.full:
            mode_info.append("full")
        if self.args.skip_performance:
            mode_info.append("skip-performance")
        if mode_info:
            self.logger.info(f"Mode: {', '.join(mode_info)}")

        # Load ETF list
        etfs = load_etf_list()
        if not etfs:
            self.logger.error("No ETFs found in database")
            return 1

        # ETFリストをコードでソート（再開時の一貫性確保）
        etfs = sorted(etfs, key=lambda x: x["code"])

        # 全ETFリストを保存（パフォーマンスキャッシュ更新用）
        all_etfs = etfs[:]

        # バッチログ開始
        self._start_batch_log(total_count=len(etfs))

        # 再開処理（last_item_code以降のETFのみ処理）
        parent_last_item_code = self.get_resume_start_code()
        if parent_last_item_code:
            resume_index = next(
                (i for i, e in enumerate(etfs) if e["code"] > parent_last_item_code),
                len(etfs),
            )
            etfs = etfs[resume_index:]
            self.logger.info(
                f"Resuming from index {resume_index}, {len(etfs)} ETFs remaining"
            )

        if self.args.limit:
            etfs = etfs[: self.args.limit]
            self.logger.info(f"Limited to first {self.args.limit} ETFs")

        self.logger.info(f"Updating {len(etfs)} ETFs...")

        success_count = 0
        fail_count = 0
        skip_count = 0

        try:
            for i, etf in enumerate(etfs, 1):
                code = etf["code"]
                self.logger.info(
                    f"[{i}/{len(etfs)}] Processing {code} ({etf.get('name', '')})"
                )

                result = update_single_etf(
                    code,
                    self.logger,
                    dry_run=self.args.dry_run,
                    full=self.args.full,
                    smart=self.args.smart,
                )
                if result == "success":
                    success_count += 1
                elif result == "skipped":
                    skip_count += 1
                else:
                    fail_count += 1

                # 進捗更新
                self._update_progress(last_item_code=code)

                # レート制限対策（最後の銘柄以外、スキップ時はsleep不要）
                if i < len(etfs) and result != "skipped":
                    time_module.sleep(self.args.rate_limit)

            # 最終進捗更新
            if etfs:
                self._final_progress_update(last_item_code=etfs[-1]["code"])

            # パフォーマンスキャッシュの更新
            if not self.args.dry_run and not self.args.skip_performance:
                self.logger.info("-" * 60)
                self.logger.info("Starting performance cache calculation...")
                # 全ETFを対象に更新（再開時も常に全件更新）
                codes = [etf["code"] for etf in all_etfs]
                perf_success, perf_fail = update_performance_cache(
                    codes, self.logger, self.args.rate_limit
                )
                self.logger.info(
                    f"Performance cache: {perf_success} success, {perf_fail} failed"
                )

            # モメンタムラベルの更新（パフォーマンスキャッシュ依存、常に実行）
            if not self.args.dry_run:
                self.logger.info("-" * 60)
                codes = [etf["code"] for etf in all_etfs]
                update_momentum_labels(codes, self.logger)

            # バッチログ終了（成功）
            # skipped は「事前判定で fetch 不要」のため処理件数に算入する。
            # 全件failed（success=0 & skip=0）のときのみ failed に補正される。
            processed_total = success_count + skip_count + fail_count
            effective_success = success_count + skip_count
            self._finish_batch_log(
                success=True,
                success_count=effective_success,
                total_count=processed_total,
            )

            self.logger.info("=" * 60)
            self.logger.info(
                f"Update completed: {success_count} success, {skip_count} skipped, {fail_count} failed"
            )
            self.logger.info("=" * 60)

            return 0 if fail_count == 0 else 1

        except Exception as e:
            # バッチログ終了（失敗）
            self._finish_batch_log(success=False, error_message=str(e))
            raise


if __name__ == "__main__":
    script = UpdateEtfDataScript()
    sys.exit(script.run())
