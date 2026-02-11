#!/usr/bin/env python3
"""Backfill momentum history data (extended/optimized version).

Optimized backfill script that populates momentum_label, regression_rate_1m,
regression_rate_3m into etf_metrics_history for up to 365 days.

Key optimization: Instead of querying PriceHistory per ETF per date,
loads 455 days (365+90) of PriceHistory per ETF in a single query,
then uses Pandas slicing for each target date window.

Usage:
    python scripts/backfill_momentum_history_extended.py
    python scripts/backfill_momentum_history_extended.py --days 365
    python scripts/backfill_momentum_history_extended.py --dry-run
    python scripts/backfill_momentum_history_extended.py --etf-code 1306
    python scripts/backfill_momentum_history_extended.py --cutoff-date 2026-02-09
"""
import os
import random
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(SCRIPT_DIR))
from base_batch import SimpleBatchScript
from update_etf_data import calculate_regression_return_from_df

from src.models import EtfMetricsHistory, PriceHistory, StockSplit, db
from src.repositories import ETFRepository, EtfMetricsHistoryRepository
from src.utils.momentum import get_momentum_label

# バックフィル対象: 1m/3mのみ
BACKFILL_PERIODS = {
    "1m": ("regression_rate_1m", 30),
    "3m": ("regression_rate_3m", 90),
}

# 455日 = 365 (バックフィル日数) + 90 (3Mウィンドウ)
LOOKBACK_BUFFER_DAYS = 90

# クロスバリデーション: 最適化版と旧方式の許容相対誤差
CROSS_VALIDATION_THRESHOLD = 0.0001


class BackfillMomentumHistoryExtendedBatch(SimpleBatchScript):
    """勢いデータの最適化バックフィルバッチ（拡張版）"""

    batch_name = "backfill_momentum_history_extended"
    description = (
        "Optimized backfill of momentum_label, regression_rate_1m/3m "
        "into etf_metrics_history (up to 365 days)"
    )

    def add_custom_arguments(self, parser):
        """カスタム引数追加"""
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of calendar days to backfill (default: 365)",
        )
        parser.add_argument(
            "--etf-code",
            type=str,
            default=None,
            help="Process only a specific ETF code (for testing)",
        )
        parser.add_argument(
            "--cutoff-date",
            type=str,
            default="2026-02-09",
            help="Cutoff date in YYYY-MM-DD format (default: 2026-02-09)",
        )

    def _parse_cutoff_date(self) -> date:
        """カットオフ日をパースする。"""
        try:
            return datetime.strptime(self.args.cutoff_date, "%Y-%m-%d").date()
        except ValueError:
            self.logger.error(
                f"Invalid cutoff-date format: {self.args.cutoff_date}"
            )
            raise

    def _get_target_dates(self, days: int, cutoff: date) -> List[date]:
        """PriceHistoryから対象日付一覧を取得する。

        カットオフ日より前の日付のみ返す。
        """
        base_date = cutoff - timedelta(days=days)
        rows = (
            db.session.query(PriceHistory.date)
            .filter(
                PriceHistory.date >= base_date,
                PriceHistory.date < cutoff,
            )
            .distinct()
            .order_by(PriceHistory.date)
            .all()
        )
        return [row.date for row in rows]

    def _load_price_history_bulk(
        self, etf_code: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """指定ETFの株価履歴を一括でDataFrameとして読み込む。

        Args:
            etf_code: ETFコード
            start_date: 開始日
            end_date: 終了日

        Returns:
            DateTimeIndex(date型)を持つDataFrame (Close列)
        """
        records = (
            PriceHistory.query.filter(
                PriceHistory.etf_code == etf_code,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date,
            )
            .order_by(PriceHistory.date)
            .all()
        )

        if not records:
            return pd.DataFrame(columns=["Close"])

        return pd.DataFrame(
            {"Close": [r.close for r in records]},
            index=[r.date for r in records],
        )

    def _apply_split_adjustments(
        self, etf_code: str, df: pd.DataFrame
    ) -> pd.DataFrame:
        """is_chart_applied=Trueの株式分割補正をDataFrameに適用する。

        chart_service.pyと同じロジック: 分割日より前の終値を
        cumulative_ratio で割って調整する。

        Args:
            etf_code: ETFコード
            df: Close列を持つDateTimeIndex DataFrame

        Returns:
            分割補正済みDataFrame
        """
        if df.empty:
            return df

        start_date = df.index.min()
        splits = (
            StockSplit.query.filter(
                StockSplit.etf_code == etf_code,
                StockSplit.is_chart_applied.is_(True),
                StockSplit.split_date >= start_date,
            )
            .order_by(StockSplit.split_date.asc())
            .all()
        )

        if not splits:
            return df

        adjusted_df = df.copy()
        for idx in adjusted_df.index:
            cumulative_ratio = 1.0
            for split in splits:
                if idx < split.split_date:
                    cumulative_ratio *= split.ratio
            if cumulative_ratio != 1.0:
                adjusted_df.at[idx, "Close"] = (
                    adjusted_df.at[idx, "Close"] / cumulative_ratio
                )

        return adjusted_df

    def _slice_window(
        self, df: pd.DataFrame, target_date: date, window_days: int
    ) -> pd.DataFrame:
        """DataFrameから指定日付を終点としたウィンドウを切り出す。

        Args:
            df: 全期間のPriceHistory DataFrame
            target_date: ウィンドウの終了日
            window_days: ウィンドウの日数（カレンダー日数）

        Returns:
            切り出されたDataFrame
        """
        window_start = target_date - timedelta(days=window_days)
        mask = (df.index >= window_start) & (df.index <= target_date)
        return df.loc[mask]

    def _diagnose_coverage(
        self, etf_codes: List[str], days: int, cutoff: date
    ) -> Dict[str, dict]:
        """PriceHistoryカバレッジ事前診断。

        Returns:
            etf_code -> {oldest_date, newest_date, count, coverage_pct}
        """
        self.logger.info("=" * 40)
        self.logger.info("PriceHistory Coverage Diagnosis")
        self.logger.info("=" * 40)

        total_needed = days + LOOKBACK_BUFFER_DAYS
        start_date = cutoff - timedelta(days=total_needed)

        coverage_map = {}
        low_coverage = 0

        for etf_code in etf_codes:
            count = (
                PriceHistory.query.filter(
                    PriceHistory.etf_code == etf_code,
                    PriceHistory.date >= start_date,
                    PriceHistory.date < cutoff,
                )
                .count()
            )

            oldest = (
                PriceHistory.query.filter(
                    PriceHistory.etf_code == etf_code,
                )
                .order_by(PriceHistory.date)
                .first()
            )

            # 営業日ベースで概算（365日 = 約245営業日）
            expected_trading_days = int(total_needed * 245 / 365)
            coverage_pct = (
                round(count / expected_trading_days * 100, 1)
                if expected_trading_days > 0
                else 0
            )

            coverage_map[etf_code] = {
                "oldest_date": oldest.date if oldest else None,
                "count": count,
                "coverage_pct": coverage_pct,
            }

            if coverage_pct < 50:
                low_coverage += 1

        self.logger.info(
            f"Total ETFs: {len(etf_codes)}, "
            f"Low coverage (<50%): {low_coverage}"
        )

        # カバレッジが低いETFを表示
        if low_coverage > 0:
            self.logger.info("ETFs with low coverage:")
            for code, info in sorted(coverage_map.items()):
                if info["coverage_pct"] < 50:
                    self.logger.info(
                        f"  {code}: {info['count']} records, "
                        f"{info['coverage_pct']}% coverage, "
                        f"oldest={info['oldest_date']}"
                    )

        self.logger.info("=" * 40)
        return coverage_map

    def _cross_validate(
        self, etf_codes: List[str], target_dates: List[date], n_samples: int = 5
    ) -> None:
        """ランダム5件を旧方式（個別クエリ版）と突合し差異を確認する。"""
        self.logger.info("=" * 40)
        self.logger.info("Cross-Validation (optimized vs legacy)")
        self.logger.info("=" * 40)

        # ランダムにサンプルを選ぶ
        samples = []
        attempts = 0
        max_attempts = n_samples * 10
        while len(samples) < n_samples and attempts < max_attempts:
            etf_code = random.choice(etf_codes)
            target_date = random.choice(target_dates)
            if (etf_code, target_date) not in samples:
                samples.append((etf_code, target_date))
            attempts += 1

        all_match = True
        for etf_code, target_date in samples:
            # 最適化版: 一括読み込み + スライス + 分割補正
            bulk_start = target_date - timedelta(days=LOOKBACK_BUFFER_DAYS)
            df_bulk = self._load_price_history_bulk(
                etf_code, bulk_start, target_date
            )
            df_bulk = self._apply_split_adjustments(etf_code, df_bulk)
            opt_rates = {}
            for period, (col, days) in BACKFILL_PERIODS.items():
                window_df = self._slice_window(df_bulk, target_date, days)
                opt_rates[col] = calculate_regression_return_from_df(
                    window_df, len(window_df)
                )

            # 旧方式: 個別クエリ + 分割補正
            legacy_rates = {}
            for period, (col, days) in BACKFILL_PERIODS.items():
                legacy_start = target_date - timedelta(days=days)
                records = (
                    PriceHistory.query.filter(
                        PriceHistory.etf_code == etf_code,
                        PriceHistory.date >= legacy_start,
                        PriceHistory.date <= target_date,
                    )
                    .order_by(PriceHistory.date)
                    .all()
                )

                if records:
                    df_legacy = pd.DataFrame(
                        {"Close": [r.close for r in records]},
                        index=[r.date for r in records],
                    )
                    df_legacy = self._apply_split_adjustments(
                        etf_code, df_legacy
                    )
                    legacy_rates[col] = calculate_regression_return_from_df(
                        df_legacy, len(df_legacy)
                    )
                else:
                    legacy_rates[col] = None

            # 比較
            match = True
            for col in ["regression_rate_1m", "regression_rate_3m"]:
                opt_val = opt_rates.get(col)
                leg_val = legacy_rates.get(col)
                if opt_val is None and leg_val is None:
                    continue
                if opt_val is None or leg_val is None:
                    match = False
                    break
                if leg_val != 0 and abs(opt_val - leg_val) / abs(leg_val) > CROSS_VALIDATION_THRESHOLD:
                    match = False
                    break
                if leg_val == 0 and opt_val != 0:
                    match = False
                    break

            status = "OK" if match else "MISMATCH"
            if not match:
                all_match = False
            self.logger.info(
                f"  [{status}] {etf_code} {target_date}: "
                f"opt={opt_rates}, legacy={legacy_rates}"
            )

        if all_match:
            self.logger.info("Cross-validation PASSED: All samples match.")
        else:
            self.logger.warning(
                "Cross-validation WARNING: Some samples have discrepancies."
            )
        self.logger.info("=" * 40)

    def _report_cutoff_diff(
        self, etf_codes: List[str], cutoff: date
    ) -> None:
        """カットオフ日直前のバックフィル済みデータとの差異を出力する。"""
        self.logger.info("=" * 40)
        self.logger.info(
            f"Diff Report: backfilled data near cutoff ({cutoff})"
        )
        self.logger.info("=" * 40)

        # PriceHistoryでカットオフ日に最も近い前日を検索
        nearest_row = (
            db.session.query(PriceHistory.date)
            .filter(PriceHistory.date < cutoff)
            .distinct()
            .order_by(PriceHistory.date.desc())
            .first()
        )
        if not nearest_row:
            self.logger.info("No data before cutoff date.")
            return

        check_date = nearest_row.date
        self.logger.info(f"Checking date: {check_date}")

        metrics_repo = EtfMetricsHistoryRepository()
        existing = metrics_repo.get_metrics_batch_for_date(etf_codes, check_date)

        diff_count = 0
        for etf_code in etf_codes:
            if etf_code not in existing:
                continue

            record = existing[etf_code]
            # 再計算（分割補正込み）
            df_bulk = self._load_price_history_bulk(
                etf_code,
                check_date - timedelta(days=LOOKBACK_BUFFER_DAYS),
                check_date,
            )
            df_bulk = self._apply_split_adjustments(etf_code, df_bulk)

            for period, (col, days) in BACKFILL_PERIODS.items():
                window_df = self._slice_window(df_bulk, check_date, days)
                new_val = calculate_regression_return_from_df(
                    window_df, len(window_df)
                )
                old_val = getattr(record, col)

                if old_val != new_val:
                    self.logger.info(
                        f"  {etf_code} {col}: "
                        f"existing={old_val} -> recalc={new_val}"
                    )
                    diff_count += 1

        if diff_count == 0:
            self.logger.info("No differences found near cutoff.")
        else:
            self.logger.info(f"Total differences: {diff_count}")
        self.logger.info("=" * 40)

    def execute(self):
        """メイン処理"""
        start_time = time.time()
        cutoff = self._parse_cutoff_date()
        days = self.args.days

        etf_repo = ETFRepository()

        # ETFリスト取得
        all_etfs = etf_repo.search(limit=None, offset=0)
        etf_codes = sorted([etf.code for etf in all_etfs])
        if self.args.etf_code:
            if self.args.etf_code not in etf_codes:
                self.logger.error(
                    f"ETF code not found: {self.args.etf_code}"
                )
                return 1
            etf_codes = [self.args.etf_code]

        self.logger.info(f"Target ETFs: {len(etf_codes)}")
        self.logger.info(f"Backfill days: {days}")
        self.logger.info(f"Cutoff date: {cutoff}")

        # カバレッジ事前診断
        self._diagnose_coverage(etf_codes, days, cutoff)

        # 対象日付リスト取得
        target_dates = self._get_target_dates(days, cutoff)
        if not target_dates:
            self.logger.info("No target dates found in PriceHistory.")
            return 0

        self.logger.info(
            f"Target dates: {len(target_dates)} "
            f"({target_dates[0]} ~ {target_dates[-1]})"
        )

        total_created = 0
        total_updated = 0
        total_skipped = 0

        # ETFごとにループ（最適化: ETF単位で一括読み込み）
        for etf_idx, etf_code in enumerate(etf_codes, 1):
            self.logger.info(
                f"[{etf_idx}/{len(etf_codes)}] Processing {etf_code}..."
            )

            # 455日分（days + 90日バッファ）のPriceHistoryを一括取得
            bulk_start = cutoff - timedelta(
                days=days + LOOKBACK_BUFFER_DAYS
            )
            df_all = self._load_price_history_bulk(
                etf_code, bulk_start, cutoff - timedelta(days=1)
            )

            # 株式分割補正を適用（is_chart_applied=Trueのみ）
            df_all = self._apply_split_adjustments(etf_code, df_all)

            if df_all.empty:
                self.logger.info(f"  No PriceHistory for {etf_code}, skipping.")
                total_skipped += len(target_dates)
                continue

            # 既存のmetrics_historyをカットオフ日前の全件取得
            existing_records = (
                EtfMetricsHistory.query.filter(
                    EtfMetricsHistory.etf_code == etf_code,
                    EtfMetricsHistory.date >= target_dates[0],
                    EtfMetricsHistory.date < cutoff,
                )
                .all()
            )
            existing_map = {r.date: r for r in existing_records}

            etf_created = 0
            etf_updated = 0
            etf_skipped = 0

            for target_date in target_dates:
                try:
                    # 1M / 3M ウィンドウのスライシングで回帰率計算
                    rates = {}
                    for period, (col, window_days) in BACKFILL_PERIODS.items():
                        window_df = self._slice_window(
                            df_all, target_date, window_days
                        )
                        rates[col] = calculate_regression_return_from_df(
                            window_df, len(window_df)
                        )

                    label = get_momentum_label(
                        rates["regression_rate_1m"],
                        rates["regression_rate_3m"],
                    )

                    if not self.args.dry_run:
                        if target_date in existing_map:
                            # 既存レコード: momentum系3カラムのみ上書き
                            record = existing_map[target_date]
                            record.momentum_label = label
                            record.regression_rate_1m = rates[
                                "regression_rate_1m"
                            ]
                            record.regression_rate_3m = rates[
                                "regression_rate_3m"
                            ]
                            etf_updated += 1
                        else:
                            # 新規作成: momentum系3カラムのみ（他はNULL）
                            record = EtfMetricsHistory(
                                etf_code=etf_code,
                                date=target_date,
                                momentum_label=label,
                                regression_rate_1m=rates[
                                    "regression_rate_1m"
                                ],
                                regression_rate_3m=rates[
                                    "regression_rate_3m"
                                ],
                            )
                            db.session.add(record)
                            etf_created += 1
                    else:
                        if target_date in existing_map:
                            etf_updated += 1
                        else:
                            etf_created += 1

                except Exception as e:
                    self.logger.error(
                        f"  Error {etf_code} on {target_date}: {e}"
                    )
                    etf_skipped += 1
                    continue

            # ETF単位でcommit（中断→再実行可能）
            if not self.args.dry_run:
                db.session.commit()

            total_created += etf_created
            total_updated += etf_updated
            total_skipped += etf_skipped

            self.logger.info(
                f"  {etf_code}: created={etf_created}, "
                f"updated={etf_updated}, skipped={etf_skipped}"
            )

        elapsed = time.time() - start_time

        self.logger.info("=" * 60)
        self.logger.info("Summary")
        self.logger.info("=" * 60)
        self.logger.info(f"Total created: {total_created}")
        self.logger.info(f"Total updated: {total_updated}")
        self.logger.info(f"Total skipped: {total_skipped}")
        self.logger.info(f"Elapsed time: {elapsed:.1f}s")

        # クロスバリデーション
        if len(etf_codes) > 0 and len(target_dates) > 0:
            self._cross_validate(etf_codes, target_dates)

        # 差異レポート
        self._report_cutoff_diff(etf_codes, cutoff)

        if self.args.dry_run:
            self.logger.info("DRY RUN - No changes were saved to DB.")

        return 0


if __name__ == "__main__":
    sys.exit(BackfillMomentumHistoryExtendedBatch().run())
