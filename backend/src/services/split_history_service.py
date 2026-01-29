"""Service for fetching and syncing historical stock split data."""
import logging
from datetime import datetime
from typing import Dict, List

import yfinance as yf

from src.models import StockSplit
from src.repositories.stock_split_repository import StockSplitRepository

logger = logging.getLogger(__name__)


class SplitHistoryService:
    """Service for managing historical stock split data."""

    def __init__(self):
        """Initialize the service."""
        self.repository = StockSplitRepository()

    def fetch_historical_splits(self, etf_code: str) -> List[dict]:
        """Fetch all historical splits from yfinance.

        Args:
            etf_code: ETF code (e.g., "1306")

        Returns:
            List of split dictionaries with keys: split_date, ratio

        Raises:
            ValueError: If no data is available for the ticker
        """
        ticker = f"{etf_code}.T"

        try:
            stock = yf.Ticker(ticker)
            splits = stock.splits

            if splits.empty:
                logger.info(f"{etf_code}: No historical splits found")
                return []

            results = []
            for split_date, ratio in splits.items():
                results.append(
                    {
                        "split_date": split_date.date(),
                        "ratio": float(ratio),
                    }
                )

            logger.info(f"{etf_code}: Found {len(results)} historical splits")
            return results

        except Exception as e:
            logger.error(f"{etf_code}: Failed to fetch splits from yfinance: {e}")
            raise ValueError(f"Failed to fetch splits for {ticker}: {e}")

    def sync_splits_for_etf(self, etf_code: str) -> Dict[str, any]:
        """Sync historical splits for a single ETF.

        Args:
            etf_code: ETF code (e.g., "1306")

        Returns:
            Dictionary with keys:
                - etf_code: The ETF code
                - fetched: Number of splits fetched from yfinance
                - registered: Number of splits newly registered
                - skipped: Number of splits already registered
                - error: Error message if failed (None if successful)
        """
        result = {
            "etf_code": etf_code,
            "fetched": 0,
            "registered": 0,
            "skipped": 0,
            "error": None,
        }

        try:
            # Fetch historical splits
            splits = self.fetch_historical_splits(etf_code)
            result["fetched"] = len(splits)

            if not splits:
                return result

            # Register each split if not already exists
            for split_data in splits:
                split_date = split_data["split_date"]
                ratio = split_data["ratio"]

                # Check if already registered
                if self.repository.exists(etf_code, split_date):
                    result["skipped"] += 1
                    logger.debug(
                        f"{etf_code}: Split on {split_date} already registered"
                    )
                    continue

                # Register new split with is_applied=False (requires admin approval)
                split = StockSplit(
                    etf_code=etf_code,
                    split_date=split_date,
                    ratio=ratio,
                    is_applied=False,
                    detected_at=datetime.utcnow(),
                    previous_close=None,
                    current_close=None,
                    change_percent=None,
                )
                self.repository.create(split)
                result["registered"] += 1
                logger.info(
                    f"{etf_code}: Registered split on {split_date} "
                    f"with ratio {ratio}"
                )

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"{etf_code}: Sync failed: {e}")

        return result

    def sync_all_etfs(self, etf_codes: List[str]) -> Dict[str, any]:
        """Sync historical splits for multiple ETFs.

        Args:
            etf_codes: List of ETF codes

        Returns:
            Dictionary with keys:
                - total: Total number of ETFs processed
                - success: Number of successful syncs
                - failed: Number of failed syncs
                - total_fetched: Total splits fetched
                - total_registered: Total splits registered
                - total_skipped: Total splits skipped
                - results: List of individual results
        """
        summary = {
            "total": len(etf_codes),
            "success": 0,
            "failed": 0,
            "total_fetched": 0,
            "total_registered": 0,
            "total_skipped": 0,
            "results": [],
        }

        for etf_code in etf_codes:
            result = self.sync_splits_for_etf(etf_code)
            summary["results"].append(result)

            if result["error"] is None:
                summary["success"] += 1
                summary["total_fetched"] += result["fetched"]
                summary["total_registered"] += result["registered"]
                summary["total_skipped"] += result["skipped"]
            else:
                summary["failed"] += 1

        return summary
