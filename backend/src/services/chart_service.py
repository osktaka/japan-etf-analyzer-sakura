"""Chart service for chart data business logic."""
from typing import Dict, List, Optional

from src.external import YahooFinanceClient
from src.repositories import ETFRepository


class ChartService:
    """Service for chart data operations."""

    VALID_PERIODS = ["1m", "3m", "6m", "1y", "3y", "5y", "10y", "20y"]

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
            period: Time period (1m, 3m, 6m, 1y, 3y, 5y, 10y, 20y)

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

    def get_batch_periods_chart_data(
        self,
        code: str,
        periods: List[str],
    ) -> Optional[Dict]:
        """Get chart data for a single ETF across multiple periods.

        Args:
            code: ETF code
            periods: List of time periods (e.g., ["3m", "6m", "1y"])

        Returns:
            Dictionary with code, name, and charts for each period,
            or None if ETF not found
        """
        etf = self.etf_repository.get_by_code(code)
        if not etf:
            return None

        charts = {}
        for period in periods:
            if period not in self.VALID_PERIODS:
                continue
            chart_data = self.yf_client.get_chart_data(code, period)
            charts[period] = chart_data

        return {
            "code": code,
            "name": etf.name,
            "charts": charts,
        }

    def get_batch_codes_chart_data(
        self,
        codes: List[str],
        period: str = "1m",
    ) -> Dict[str, Dict]:
        """Get chart data for multiple ETFs with a single period.

        Args:
            codes: List of ETF codes
            period: Time period

        Returns:
            Dictionary keyed by code with chart data for each ETF
        """
        if period not in self.VALID_PERIODS:
            period = "1m"

        results = {}
        for code in codes:
            chart_data = self.get_chart_data(code, period)
            if chart_data:
                results[code] = chart_data

        return results
