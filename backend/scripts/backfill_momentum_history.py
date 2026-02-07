#!/usr/bin/env python3
"""Backfill momentum history data for etf_metrics_history.

One-time manual script to populate momentum_label, regression_rate_1m,
regression_rate_3m from PriceHistory data. Created for migration 009 (commit 9061ff6).

Usage:
    python scripts/backfill_momentum_history.py [--days N] [--dry-run]
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
from update_etf_data import calculate_regression_return_from_df

from src.models import EtfMetricsHistory, PriceHistory, db
from src.repositories import ETFRepository, EtfMetricsHistoryRepository
from src.utils.momentum import get_momentum_label


class BackfillMomentumHistoryBatch(SimpleBatchScript):
    """勢いデータのバックフィルバッチ"""

    batch_name = "backfill_momentum_history"
    description = (
        "Backfill momentum_label, regression_rate_1m/3m into etf_metrics_history"
    )

    def add_custom_arguments(self, parser):
        """カスタム引数追加"""
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of calendar days to backfill (default: 30)",
        )

    def _get_target_dates(self, days):
        """PriceHistoryから対象日付一覧を取得する。

        Args:
            days: 遡るカレンダー日数

        Returns:
            対象日付のリスト（昇順）
        """
        base_date = date.today() - timedelta(days=days)
        rows = (
            db.session.query(PriceHistory.date)
            .filter(PriceHistory.date >= base_date)
            .distinct()
            .order_by(PriceHistory.date)
            .all()
        )
        return [row.date for row in rows]

    def _get_price_history(self, etf_code, end_date, lookback_days=90):
        """指定ETFの株価履歴をDataFrameで返す。

        Args:
            etf_code: ETFコード
            end_date: 終了日（この日を含む）
            lookback_days: 遡る日数（カレンダー日）

        Returns:
            Closeカラムを持つDataFrame
        """
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

    def execute(self):
        """メイン処理"""
        etf_repo = ETFRepository()
        metrics_repo = EtfMetricsHistoryRepository()

        # 全ETFコードを取得
        all_etfs = etf_repo.search(limit=None, offset=0)
        etf_codes = sorted([etf.code for etf in all_etfs])
        self.logger.info(f"Target ETFs: {len(etf_codes)}")

        # 対象日付を取得
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

            # 既存レコードを一括取得
            existing = metrics_repo.get_metrics_batch_for_date(etf_codes, target_date)

            date_updated = 0
            date_created = 0

            for etf_code in etf_codes:
                try:
                    # PriceHistoryからDataFrame構築（期間別に暦日ベースで取得）
                    df_1m = self._get_price_history(
                        etf_code, target_date, lookback_days=30
                    )
                    df_3m = self._get_price_history(
                        etf_code, target_date, lookback_days=90
                    )

                    # 回帰率計算（取得した全データポイントを使用）
                    rate_1m = calculate_regression_return_from_df(
                        df_1m, len(df_1m)
                    )
                    rate_3m = calculate_regression_return_from_df(
                        df_3m, len(df_3m)
                    )
                    label = get_momentum_label(rate_1m, rate_3m)

                    if not self.args.dry_run:
                        if etf_code in existing:
                            # 既存レコード: 3カラムのみ更新（ORM dirty tracking）
                            record = existing[etf_code]
                            record.momentum_label = label
                            record.regression_rate_1m = rate_1m
                            record.regression_rate_3m = rate_3m
                            date_updated += 1
                        else:
                            # 新規レコード: 勢い3カラムのみで作成
                            record = EtfMetricsHistory(
                                etf_code=etf_code,
                                date=target_date,
                                momentum_label=label,
                                regression_rate_1m=rate_1m,
                                regression_rate_3m=rate_3m,
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
                f"  {target_date}: updated={date_updated}, " f"created={date_created}"
            )

        self.logger.info(
            f"Completed: total updated={total_updated}, "
            f"total created={total_created}"
        )
        if self.args.dry_run:
            self.logger.info("DRY RUN - No changes were saved to DB.")

        return 0


if __name__ == "__main__":
    sys.exit(BackfillMomentumHistoryBatch().run())
