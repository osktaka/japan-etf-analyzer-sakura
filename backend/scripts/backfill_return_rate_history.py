#!/usr/bin/env python3
"""Backfill return rate history data for etf_metrics_history.

One-time manual script to populate return_rate_1m, return_rate_3m
from PriceHistory data. After backfill, verifies latest date against
PerformanceCache and corrects any discrepancies.

Usage:
    python scripts/backfill_return_rate_history.py [--days N] [--dry-run]
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

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
from update_etf_data import calculate_return_from_df

from src.models import EtfMetricsHistory, PerformanceCache, PriceHistory, db
from src.repositories import ETFRepository, EtfMetricsHistoryRepository

# バックフィル対象: 1m/3mのみ（他の期間は日次バッチで蓄積）
BACKFILL_PERIODS = {
    "1m": ("return_rate_1m", 30),
    "3m": ("return_rate_3m", 90),
}


class BackfillReturnRateHistoryBatch(SimpleBatchScript):
    """リターン率データのバックフィルバッチ"""

    batch_name = "backfill_return_rate_history"
    description = "Backfill return_rate_1m/3m into etf_metrics_history"

    def add_custom_arguments(self, parser):
        """カスタム引数追加"""
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of calendar days to backfill (default: 30)",
        )

    def _get_target_dates(self, days):
        """PriceHistoryから対象日付一覧を取得する。"""
        base_date = date.today() - timedelta(days=days)
        rows = (
            db.session.query(PriceHistory.date)
            .filter(PriceHistory.date >= base_date)
            .distinct()
            .order_by(PriceHistory.date)
            .all()
        )
        return [row.date for row in rows]

    def _get_price_history(self, etf_code, end_date, lookback_days):
        """指定ETFの株価履歴をDataFrameで返す。"""
        start_date = end_date - timedelta(days=lookback_days)
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

    def _verify_and_fix_latest(self, etf_codes, latest_date):
        """最新日の値をPerformanceCacheと比較し、差異があれば修正する。"""
        self.logger.info(f"Verifying latest date ({latest_date}) against PerformanceCache...")

        # PerformanceCacheから1m/3mの値を一括取得
        pc_records = (
            PerformanceCache.query.filter(
                PerformanceCache.etf_code.in_(etf_codes),
                PerformanceCache.period.in_(["1m", "3m"]),
            )
            .all()
        )
        pc_map = {}
        for r in pc_records:
            pc_map.setdefault(r.etf_code, {})[r.period] = r.return_rate

        # etf_metrics_historyの最新日レコード取得
        metrics_repo = EtfMetricsHistoryRepository()
        existing = metrics_repo.get_metrics_batch_for_date(etf_codes, latest_date)

        fixed_count = 0
        for etf_code in etf_codes:
            if etf_code not in existing or etf_code not in pc_map:
                continue

            record = existing[etf_code]
            pc_data = pc_map[etf_code]
            changed = False

            for period, (col, _days) in BACKFILL_PERIODS.items():
                pc_val = pc_data.get(period)
                hist_val = getattr(record, col)
                if pc_val is not None and hist_val != pc_val:
                    self.logger.info(
                        f"  Fix {etf_code} {col}: {hist_val} -> {pc_val}"
                    )
                    setattr(record, col, pc_val)
                    changed = True

            if changed:
                fixed_count += 1

        if fixed_count > 0:
            db.session.commit()
            self.logger.info(f"Fixed {fixed_count} ETFs on {latest_date}")
        else:
            self.logger.info("All values match PerformanceCache.")

    def execute(self):
        """メイン処理"""
        etf_repo = ETFRepository()
        metrics_repo = EtfMetricsHistoryRepository()

        all_etfs = etf_repo.search(limit=None, offset=0)
        etf_codes = sorted([etf.code for etf in all_etfs])
        self.logger.info(f"Target ETFs: {len(etf_codes)}")

        target_dates = self._get_target_dates(self.args.days)
        if not target_dates:
            self.logger.info("No target dates found in PriceHistory.")
            return 0

        self.logger.info(
            f"Target dates: {len(target_dates)} "
            f"({target_dates[0]} ~ {target_dates[-1]})"
        )

        total_updated = 0
        total_created = 0

        for date_idx, target_date in enumerate(target_dates, 1):
            self.logger.info(
                f"[{date_idx}/{len(target_dates)}] Processing {target_date}..."
            )

            existing = metrics_repo.get_metrics_batch_for_date(etf_codes, target_date)

            date_updated = 0
            date_created = 0

            for etf_code in etf_codes:
                try:
                    rates = {}
                    for period, (col, days) in BACKFILL_PERIODS.items():
                        df = self._get_price_history(etf_code, target_date, days)
                        rates[col] = calculate_return_from_df(df, len(df))

                    if not self.args.dry_run:
                        if etf_code in existing:
                            record = existing[etf_code]
                            for col, value in rates.items():
                                setattr(record, col, value)
                            date_updated += 1
                        else:
                            record = EtfMetricsHistory(
                                etf_code=etf_code,
                                date=target_date,
                                **rates,
                            )
                            db.session.add(record)
                            date_created += 1
                    else:
                        if etf_code in existing:
                            date_updated += 1
                        else:
                            date_created += 1

                except Exception as e:
                    self.logger.error(
                        f"Error processing {etf_code} on {target_date}: {e}"
                    )
                    continue

            if not self.args.dry_run:
                db.session.commit()

            total_updated += date_updated
            total_created += date_created

            self.logger.info(
                f"  {target_date}: updated={date_updated}, created={date_created}"
            )

        self.logger.info(
            f"Completed: total updated={total_updated}, "
            f"total created={total_created}"
        )

        # 最新日をPerformanceCacheと比較・修正
        if not self.args.dry_run:
            self._verify_and_fix_latest(etf_codes, target_dates[-1])

        if self.args.dry_run:
            self.logger.info("DRY RUN - No changes were saved to DB.")

        return 0


if __name__ == "__main__":
    sys.exit(BackfillReturnRateHistoryBatch().run())
