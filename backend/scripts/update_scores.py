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
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from base_batch import BaseBatchScript

from src.models import PerformanceCache
from src.repositories import (
    ETFRepository,
    ScoreCacheRepository,
    EtfMetricsHistoryRepository,
)
from src.services.scoring_service import ScoringService
from src.utils.momentum import get_momentum_label


PERSPECTIVES = ["dividend", "low-cost", "stability", "volume", "growth", "balance"]


class UpdateScoresBatch(BaseBatchScript):
    """スコアキャッシュ更新バッチ"""

    batch_name = "update_scores"
    description = "Update score cache for all ETFs"

    # 機能フラグ設定
    enable_batch_log = True
    enable_progress = True
    enable_resume = True
    progress_interval = 10

    def add_custom_arguments(self, parser: argparse.ArgumentParser) -> None:
        """カスタム引数追加"""
        parser.add_argument(
            "--limit",
            type=int,
            help="Only update first N ETFs (for testing)",
        )

    def execute(self) -> int:
        """メイン処理"""
        etf_repo = ETFRepository()
        score_cache_repo = ScoreCacheRepository()
        scoring_service = ScoringService()

        # Get all ETFs
        all_etfs = etf_repo.search(limit=None, offset=0)
        all_etf_codes = [etf.code for etf in all_etfs]

        # ETFリストをコードでソート（再開時の一貫性確保）
        all_etfs = sorted(all_etfs, key=lambda x: x.code)

        # バッチログ開始
        self._start_batch_log(total_count=len(all_etfs))

        # resume時の開始コード取得
        parent_last_item_code = self.get_resume_start_code()
        if parent_last_item_code:
            self.logger.info(f"Resuming from last_item_code={parent_last_item_code}")

        # 処理対象のETFリストを決定
        if self.args.limit:
            etfs = all_etfs[: self.args.limit]
        else:
            etfs = all_etfs

        # 再開処理（last_item_code以降のETFのみ処理）
        if parent_last_item_code:
            resume_index = next(
                (i for i, e in enumerate(etfs) if e.code > parent_last_item_code),
                len(etfs),
            )
            etfs = etfs[resume_index:]
            self.logger.info(
                f"Resuming from index {resume_index}, {len(etfs)} ETFs remaining"
            )

        total_etfs = len(etfs)
        self.logger.info(f"Processing {total_etfs} ETFs...")

        try:
            # Batch fetch data for ALL ETFs (for percentile calculation)
            self.logger.info("Fetching data for percentile calculation...")
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
                self.logger.info(
                    f"[{idx}/{total_etfs}] Processing {etf.code} ({etf.name})..."
                )

                try:
                    # Calculate scores for all perspectives
                    for perspective in PERSPECTIVES:
                        # Calculate total score (partial mode - default)
                        total_score = scoring_service.calculate_score(
                            etf, perspective, mode="partial"
                        )

                        # Calculate total score (full mode - all 5 axes)
                        total_score_full = scoring_service.calculate_score(
                            etf, perspective, mode="full"
                        )

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

                        if not self.args.dry_run:
                            # Save to cache
                            score_cache_repo.upsert(
                                etf_code=etf.code,
                                perspective=perspective,
                                total_score=round(total_score, 1),
                                total_score_full=round(total_score_full, 1),
                                axis_scores=axis_scores,
                            )
                        else:
                            self.logger.info(
                                f"  {perspective}: partial={total_score:.1f}, "
                                f"full={total_score_full:.1f} (dry-run)"
                            )

                    updated_count += 1

                    # 進捗更新
                    self._update_progress(last_item_code=etf.code)

                except Exception as e:
                    self.logger.error(f"Error processing {etf.code}: {e}")
                    skipped_count += 1
                    continue

            # 最終進捗更新
            self._final_progress_update(last_item_code=etfs[-1].code if etfs else None)

            # 評価スコア項目の履歴保存
            if not self.args.dry_run:
                self._save_metrics_history(all_etfs)

            # バッチログ終了（成功）
            self._finish_batch_log(success=True)

            self.logger.info(
                f"Completed: {updated_count} updated, {skipped_count} skipped"
            )
            return 0

        except Exception as e:
            # バッチログ終了（失敗）
            self._finish_batch_log(success=False, error_message=str(e))
            raise

        finally:
            # Clear cache
            scoring_service._avg_volumes_cache = {}
            scoring_service._return_rates_cache = {}

    def _save_metrics_history(self, etfs) -> None:
        """評価スコア項目の履歴を保存する。

        Args:
            etfs: ETFオブジェクトのリスト
        """
        self.logger.info("Saving metrics history...")
        metrics_repo = EtfMetricsHistoryRepository()
        today = date.today()

        # performance_cacheからreturn_1y, return_3y, volatilityを取得
        etf_codes = [etf.code for etf in etfs]
        performance_data = {}
        perf_records = PerformanceCache.query.filter(
            PerformanceCache.etf_code.in_(etf_codes)
        ).all()

        # 期間→regression_rateカラム名のマッピング
        regression_period_map = {
            "1m": "regression_rate_1m",
            "3m": "regression_rate_3m",
            "6m": "regression_rate_6m",
            "1y": "regression_rate_1y",
            "3y": "regression_rate_3y",
            "5y": "regression_rate_5y",
            "10y": "regression_rate_10y",
            "20y": "regression_rate_20y",
        }

        # 期間→return_rateカラム名のマッピング
        return_period_map = {
            "1m": "return_rate_1m",
            "3m": "return_rate_3m",
            "6m": "return_rate_6m",
            "1y": "return_rate_1y",
            "3y": "return_rate_3y",
            "5y": "return_rate_5y",
            "10y": "return_rate_10y",
            "20y": "return_rate_20y",
        }

        for record in perf_records:
            if record.etf_code not in performance_data:
                performance_data[record.etf_code] = {}
            if record.period == "1y":
                performance_data[record.etf_code]["return_1y"] = record.return_rate
                performance_data[record.etf_code]["volatility"] = record.volatility
            elif record.period == "3y":
                performance_data[record.etf_code]["return_3y"] = record.return_rate

            # regression_rateを全期間で取得
            regression_key = regression_period_map.get(record.period)
            if regression_key and record.regression_rate is not None:
                performance_data[record.etf_code][
                    regression_key
                ] = record.regression_rate

            # return_rateを全期間で取得
            return_key = return_period_map.get(record.period)
            if return_key and record.return_rate is not None:
                performance_data[record.etf_code][return_key] = record.return_rate

        # 一括保存用のレコードを作成
        records = []
        for etf in etfs:
            perf = performance_data.get(etf.code, {})
            rate_1m = perf.get("regression_rate_1m")
            rate_3m = perf.get("regression_rate_3m")
            label = get_momentum_label(rate_1m, rate_3m)
            records.append(
                {
                    "etf_code": etf.code,
                    "dividend_yield": float(etf.dividend_yield)
                    if etf.dividend_yield
                    else None,
                    "expense_ratio": float(etf.expense_ratio)
                    if etf.expense_ratio
                    else None,
                    "total_assets": float(etf.total_assets)
                    if etf.total_assets
                    else None,
                    "deviation_rate": float(etf.deviation_rate)
                    if etf.deviation_rate
                    else None,
                    "return_1y": perf.get("return_1y"),
                    "return_3y": perf.get("return_3y"),
                    "volatility": perf.get("volatility"),
                    "momentum_label": label,
                    "regression_rate_1m": rate_1m,
                    "regression_rate_3m": rate_3m,
                    "regression_rate_6m": perf.get("regression_rate_6m"),
                    "regression_rate_1y": perf.get("regression_rate_1y"),
                    "regression_rate_3y": perf.get("regression_rate_3y"),
                    "regression_rate_5y": perf.get("regression_rate_5y"),
                    "regression_rate_10y": perf.get("regression_rate_10y"),
                    "regression_rate_20y": perf.get("regression_rate_20y"),
                    "return_rate_1m": perf.get("return_rate_1m"),
                    "return_rate_3m": perf.get("return_rate_3m"),
                    "return_rate_6m": perf.get("return_rate_6m"),
                    "return_rate_1y": perf.get("return_rate_1y"),
                    "return_rate_3y": perf.get("return_rate_3y"),
                    "return_rate_5y": perf.get("return_rate_5y"),
                    "return_rate_10y": perf.get("return_rate_10y"),
                    "return_rate_20y": perf.get("return_rate_20y"),
                }
            )

        # バルクUPSERT
        count = metrics_repo.bulk_upsert(records, today)
        self.logger.info(f"Saved {count} metrics history records for {today}")


if __name__ == "__main__":
    sys.exit(UpdateScoresBatch().run())
