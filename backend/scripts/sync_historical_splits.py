"""Sync historical stock splits from yfinance to database."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from base_batch import BaseBatchScript  # noqa: E402
from src.repositories import ETFRepository  # noqa: E402
from src.services.split_history_service import SplitHistoryService  # noqa: E402


def print_summary(summary: dict):
    """Print sync summary."""
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    print(f"Total ETFs:        {summary['total']}")
    print(f"Success:           {summary['success']}")
    print(f"Failed:            {summary['failed']}")
    print(f"Total Fetched:     {summary['total_fetched']}")
    print(f"Total Registered:  {summary['total_registered']}")
    print(f"Total Skipped:     {summary['total_skipped']}")
    print("=" * 60)


def print_detail(results: list):
    """Print detailed results."""
    print("\nDETAILED RESULTS:")
    print("-" * 60)
    for result in results:
        status = "✓" if result["error"] is None else "✗"
        print(
            f"{status} {result['etf_code']}: "
            f"fetched={result['fetched']}, "
            f"registered={result['registered']}, "
            f"skipped={result['skipped']}"
        )
        if result["error"]:
            print(f"  Error: {result['error']}")
    print("-" * 60)


class SyncHistoricalSplitsScript(BaseBatchScript):
    """Historical stock splits sync batch script."""

    batch_name = "sync_historical_splits"
    description = "Sync historical stock splits from yfinance"
    enable_batch_log = True
    enable_progress = False
    enable_resume = False

    def add_custom_arguments(self, parser):
        """カスタム引数を追加"""
        parser.add_argument(
            "--code",
            type=str,
            help="ETF code to sync (e.g., 1306). If not specified, sync all ETFs.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Sync all ETFs in the master",
        )
        parser.add_argument(
            "--rate-limit",
            type=float,
            default=1.0,
            help="Rate limit in seconds between requests (default: 1.0)",
        )

    def execute(self) -> int:
        """メイン処理"""
        etf_repo = ETFRepository()
        service = SplitHistoryService()

        # Determine target ETF codes
        if self.args.code:
            etf_codes = [self.args.code]
            self.logger.info(f"Target: Single ETF ({self.args.code})")
        elif self.args.all:
            etfs = etf_repo.get_all()
            etf_codes = [etf.code for etf in etfs]
            self.logger.info(f"Target: All ETFs ({len(etf_codes)} ETFs)")
        else:
            self.logger.error("Error: Please specify --code or --all")
            return 1

        # Dry run mode
        if self.args.dry_run:
            self.logger.info("\nDRY RUN MODE - No data will be synced")
            self.logger.info("=" * 60)
            self.logger.info(f"Total ETFs to sync: {len(etf_codes)}")
            self.logger.info("\nETF Codes:")
            for i, code in enumerate(etf_codes, 1):
                self.logger.info(f"  {i:3d}. {code}")
            self.logger.info("=" * 60)
            self.logger.info("\nTo execute sync, run without --dry-run option")
            return 0

        # バッチログ開始
        self._start_batch_log()

        try:
            # Execute sync
            self.logger.info(f"Syncing {len(etf_codes)} ETF(s)...")
            self.logger.info(f"Rate limit: {self.args.rate_limit} sec/request")
            self.logger.info("=" * 60)

            results = []
            for i, etf_code in enumerate(etf_codes, 1):
                self.logger.info(
                    f"[{i}/{len(etf_codes)}] Processing {etf_code}..."
                )

                result = service.sync_splits_for_etf(etf_code)
                results.append(result)

                if result["error"] is None:
                    self.logger.info(
                        f"  ✓ (fetched={result['fetched']}, "
                        f"registered={result['registered']}, "
                        f"skipped={result['skipped']})"
                    )
                else:
                    self.logger.error(f"  ✗ Error: {result['error']}")

                # Rate limiting (except for last item)
                if i < len(etf_codes):
                    time.sleep(self.args.rate_limit)

            # Summary
            summary = {
                "total": len(etf_codes),
                "success": sum(1 for r in results if r["error"] is None),
                "failed": sum(1 for r in results if r["error"] is not None),
                "total_fetched": sum(r["fetched"] for r in results),
                "total_registered": sum(r["registered"] for r in results),
                "total_skipped": sum(r["skipped"] for r in results),
            }

            print_summary(summary)

            # Detailed results if requested
            if summary["failed"] > 0:
                self.logger.warning("\nFailed ETFs:")
                for result in results:
                    if result["error"]:
                        self.logger.warning(f"  - {result['etf_code']}: {result['error']}")

            # バッチログ終了（成功）
            self._finish_batch_log(success=True)
            return 0

        except Exception as e:
            # バッチログ終了（失敗）
            self._finish_batch_log(success=False, error_message=str(e))
            raise


if __name__ == "__main__":
    script = SyncHistoricalSplitsScript()
    sys.exit(script.run())
