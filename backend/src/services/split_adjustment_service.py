"""Service for calculating stock split adjustments."""
from datetime import date
from typing import Dict, Optional, Tuple

from src.repositories.stock_split_repository import StockSplitRepository


class SplitAdjustmentService:
    """Service for calculating split adjustment factors."""

    def __init__(self, stock_split_repository: Optional[StockSplitRepository] = None):
        """Initialize split adjustment service."""
        self.stock_split_repository = stock_split_repository or StockSplitRepository()
        self._cache: Dict[Tuple[str, date], float] = {}
        self._at_date_cache: Dict[Tuple[str, date, date], float] = {}

    def clear_cache(self) -> None:
        """Clear all cached adjustment factors."""
        self._cache.clear()
        self._at_date_cache.clear()

    def get_adjustment_factor(self, etf_code: str, trade_date: date) -> float:
        """
        Calculate cumulative split adjustment factor from trade date to now.

        Args:
            etf_code: ETF code
            trade_date: Trade execution date

        Returns:
            Cumulative adjustment factor (e.g., 2.0 for 2-for-1 split)
            Returns 1.0 if no splits occurred

        Example:
            If 2-for-1 split and 1.5-for-1 split occurred after trade_date:
            factor = 2.0 * 1.5 = 3.0
        """
        cache_key = (etf_code, trade_date)
        if cache_key in self._cache:
            return self._cache[cache_key]

        splits = self.stock_split_repository.get_approved_splits_since(
            etf_code, trade_date
        )

        # Calculate cumulative factor
        cumulative_factor = 1.0
        for split in splits:
            cumulative_factor *= split.ratio

        self._cache[cache_key] = cumulative_factor
        return cumulative_factor

    def get_adjustment_factor_at_date(
        self, etf_code: str, trade_date: date, target_date: date
    ) -> float:
        """
        Calculate cumulative split adjustment factor from trade date to target date.

        Args:
            etf_code: ETF code
            trade_date: Trade execution date
            target_date: Date to calculate adjustment for

        Returns:
            Cumulative adjustment factor
            Returns 1.0 if no splits occurred between the dates

        Note:
            Unlike get_adjustment_factor which calculates to today,
            this calculates to a specific target date.
        """
        if target_date <= trade_date:
            return 1.0

        cache_key = (etf_code, trade_date, target_date)
        if cache_key in self._at_date_cache:
            return self._at_date_cache[cache_key]

        splits = self.stock_split_repository.get_approved_splits_between(
            etf_code, trade_date, target_date
        )

        cumulative_factor = 1.0
        for split in splits:
            cumulative_factor *= split.ratio

        self._at_date_cache[cache_key] = cumulative_factor
        return cumulative_factor
