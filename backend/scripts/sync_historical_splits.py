"""Sync historical stock splits from yfinance to database."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.app import create_app  # noqa: E402
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


def main():
    """Run historical split sync."""
    parser = argparse.ArgumentParser(
        description="Sync historical stock splits from yfinance"
    )
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
        "--dry-run",
        action="store_true",
        help="Preview target ETFs without syncing",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Rate limit in seconds between requests (default: 1.0)",
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        etf_repo = ETFRepository()
        service = SplitHistoryService()

        # Determine target ETF codes
        if args.code:
            etf_codes = [args.code]
            print(f"Target: Single ETF ({args.code})")
        elif args.all:
            etfs = etf_repo.get_all()
            etf_codes = [etf.code for etf in etfs]
            print(f"Target: All ETFs ({len(etf_codes)} ETFs)")
        else:
            print("Error: Please specify --code or --all")
            parser.print_help()
            sys.exit(1)

        # Dry run mode
        if args.dry_run:
            print("\nDRY RUN MODE - No data will be synced")
            print("=" * 60)
            print(f"Total ETFs to sync: {len(etf_codes)}")
            print("\nETF Codes:")
            for i, code in enumerate(etf_codes, 1):
                print(f"  {i:3d}. {code}")
            print("=" * 60)
            print("\nTo execute sync, run without --dry-run option")
            return

        # Execute sync
        print(f"\nSyncing {len(etf_codes)} ETF(s)...")
        print(f"Rate limit: {args.rate_limit} sec/request")
        print("=" * 60)

        results = []
        for i, etf_code in enumerate(etf_codes, 1):
            print(
                f"[{i}/{len(etf_codes)}] Processing {etf_code}...", end=" ", flush=True
            )

            result = service.sync_splits_for_etf(etf_code)
            results.append(result)

            if result["error"] is None:
                print(
                    f"✓ (fetched={result['fetched']}, "
                    f"registered={result['registered']}, "
                    f"skipped={result['skipped']})"
                )
            else:
                print(f"✗ Error: {result['error']}")

            # Rate limiting (except for last item)
            if i < len(etf_codes):
                time.sleep(args.rate_limit)

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
            print("\nFailed ETFs:")
            for result in results:
                if result["error"]:
                    print(f"  - {result['etf_code']}: {result['error']}")


if __name__ == "__main__":
    main()
