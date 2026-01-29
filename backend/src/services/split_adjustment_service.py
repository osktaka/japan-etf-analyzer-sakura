"""Service for calculating stock split adjustments."""
from datetime import date
from typing import Optional

from src.repositories.stock_split_repository import StockSplitRepository


class SplitAdjustmentService:
    """Service for calculating split adjustment factors."""

    def __init__(self, stock_split_repository: Optional[StockSplitRepository] = None):
        """Initialize split adjustment service."""
        self.stock_split_repository = stock_split_repository or StockSplitRepository()

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
        splits = self.stock_split_repository.get_approved_splits_since(
            etf_code, trade_date
        )

        # Calculate cumulative factor
        cumulative_factor = 1.0
        for split in splits:
            cumulative_factor *= split.ratio

        return cumulative_factor
