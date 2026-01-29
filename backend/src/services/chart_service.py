"""Chart service for chart data business logic."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.external import YahooFinanceClient
from src.repositories import ETFRepository
from src.repositories.stock_split_repository import StockSplitRepository


class ChartService:
    """Service for chart data operations."""

    VALID_PERIODS = ["1m", "3m", "6m", "1y", "3y", "5y", "10y", "20y"]

    def __init__(self):
        """Initialize service."""
        self.etf_repository = ETFRepository()
        self.yf_client = YahooFinanceClient()
        self.stock_split_repository = StockSplitRepository()

    def _apply_split_adjustments(
        self, code: str, chart_data: List[Dict], period_days: int
    ) -> List[Dict]:
        """Apply stock split adjustments to chart data.

        Args:
            code: ETF code
            chart_data: Raw chart data from yfinance
            period_days: Number of days in the chart period

        Returns:
            Adjusted chart data
        """
        if not chart_data:
            return chart_data

        # Get the start date of the chart period
        start_date = (datetime.now() - timedelta(days=period_days)).date()

        # Get all chart-applied splits since the start date
        splits = self.stock_split_repository.get_chart_applied_splits_since(
            code, start_date
        )

        if not splits:
            return chart_data

        # Apply split adjustments
        adjusted_data = []
        for point in chart_data:
            point_date_str = point.get("date")
            if not point_date_str:
                adjusted_data.append(point)
                continue

            # Parse the date string (format: "YYYY-MM-DD")
            point_date = datetime.fromisoformat(point_date_str.replace("Z", "")).date()

            # Calculate cumulative split ratio for dates before each split
            cumulative_ratio = 1.0
            for split in splits:
                if point_date < split.split_date:
                    cumulative_ratio *= split.ratio

            # Apply adjustment to price fields
            adjusted_point = point.copy()
            if cumulative_ratio != 1.0:
                for field in ["open", "high", "low", "close"]:
                    if field in adjusted_point and adjusted_point[field] is not None:
                        adjusted_point[field] = adjusted_point[field] / cumulative_ratio

            adjusted_data.append(adjusted_point)

        return adjusted_data

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

        # Apply stock split adjustments
        from src.external.yahoo_finance import YahooFinanceClient

        period_days = YahooFinanceClient.PERIOD_DAYS.get(period, 30)
        adjusted_data = self._apply_split_adjustments(code, chart_data, period_days)

        return {
            "code": code,
            "name": etf.name,
            "period": period,
            "data": adjusted_data,
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
        from src.external.yahoo_finance import YahooFinanceClient

        etf = self.etf_repository.get_by_code(code)
        if not etf:
            return None

        charts = {}
        for period in periods:
            if period not in self.VALID_PERIODS:
                continue
            chart_data = self.yf_client.get_chart_data(code, period)
            # Apply stock split adjustments
            period_days = YahooFinanceClient.PERIOD_DAYS.get(period, 30)
            adjusted_data = self._apply_split_adjustments(code, chart_data, period_days)
            charts[period] = adjusted_data

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
