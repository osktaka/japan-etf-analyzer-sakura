"""Chart service for chart data business logic."""
from typing import Dict, List, Optional

from src.external import YahooFinanceClient
from src.repositories import ETFRepository


class ChartService:
    """Service for chart data operations."""

    VALID_PERIODS = ["1w", "1m", "3m", "6m", "1y", "3y"]

    def __init__(self):
        """Initialize service."""
        self.etf_repository = ETFRepository()
        self.yf_client = YahooFinanceClient()

    def get_chart_data(
        self,
        code: str,
        period: str = "1m",
    ) -> Optional[Dict]:
        """Get chart data for an ETF.

        Args:
            code: ETF code
            period: Time period (1w, 1m, 3m, 6m, 1y, 3y)

        Returns:
            Chart data dictionary or None if ETF not found
        """
        etf = self.etf_repository.get_by_code(code)
        if not etf:
            return None

        if period not in self.VALID_PERIODS:
            period = "1m"

        chart_data = self.yf_client.get_chart_data(code, period)

        return {
            "code": code,
            "name": etf.name,
            "period": period,
            "data": chart_data,
        }

    def get_compare_chart_data(
        self,
        codes: List[str],
        period: str = "1m",
    ) -> List[Dict]:
        """Get chart data for multiple ETFs for comparison.

        Args:
            codes: List of ETF codes
            period: Time period

        Returns:
            List of chart data dictionaries
        """
        results = []
        for code in codes:
            chart_data = self.get_chart_data(code, period)
            if chart_data:
                results.append(chart_data)

        return results
