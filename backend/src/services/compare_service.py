"""Compare service for ETF performance comparison."""
import math
from typing import Dict, List, Optional

from src.services.chart_service import ChartService


class CompareService:
    """Service for comparing ETF performance metrics."""

    PERIODS = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "3y": 1095,
        "5y": 1825,
        "10y": 3650,
        "20y": 7300,
    }

    def __init__(self):
        """Initialize service with chart service."""
        self.chart_service = ChartService()

    def get_performance(self, code: str) -> Dict:
        """Get performance metrics for an ETF.

        Args:
            code: ETF code

        Returns:
            Dictionary with performance metrics for each period
        """
        result = {"code": code, "returns": {}, "volatility": None}

        # Calculate returns for each period
        for period_id, days in self.PERIODS.items():
            return_value = self._calculate_return(code, days)
            result["returns"][period_id] = return_value

        # Calculate volatility using 1 year data
        result["volatility"] = self._calculate_volatility(code, 365)

        return result

    def get_comparison(self, codes: List[str]) -> Dict:
        """Get performance comparison for multiple ETFs.

        Args:
            codes: List of ETF codes

        Returns:
            Dictionary with comparison data
        """
        performances = []
        for code in codes:
            perf = self.get_performance(code)
            performances.append(perf)

        return {
            "items": performances,
            "periods": list(self.PERIODS.keys()),
        }

    def _calculate_return(self, code: str, days: int) -> Optional[float]:
        """Calculate return for a given period.

        Args:
            code: ETF code
            days: Number of days to look back

        Returns:
            Return percentage or None if data unavailable
        """
        # Map days to chart period
        period = self._days_to_period(days)
        result = self.chart_service.get_chart_data(code, period)

        if not result or not result.get("data"):
            return None

        chart_data = result["data"]
        if len(chart_data) < 2:
            return None

        # Get first and last prices
        first_price = chart_data[0].get("close")
        last_price = chart_data[-1].get("close")

        if first_price is None or last_price is None or first_price == 0:
            return None

        return ((last_price - first_price) / first_price) * 100

    def _calculate_volatility(self, code: str, days: int) -> Optional[float]:
        """Calculate annualized volatility (standard deviation of returns).

        Args:
            code: ETF code
            days: Number of days to analyze

        Returns:
            Annualized volatility percentage or None if data unavailable
        """
        period = self._days_to_period(days)
        result = self.chart_service.get_chart_data(code, period)

        if not result or not result.get("data"):
            return None

        chart_data = result["data"]
        if len(chart_data) < 10:
            return None

        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(chart_data)):
            prev_close = chart_data[i - 1].get("close")
            curr_close = chart_data[i].get("close")

            if prev_close and curr_close and prev_close > 0:
                daily_return = (curr_close - prev_close) / prev_close
                daily_returns.append(daily_return)

        if len(daily_returns) < 5:
            return None

        # Calculate standard deviation
        mean = sum(daily_returns) / len(daily_returns)
        variance = sum((r - mean) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = math.sqrt(variance)

        # Annualize (multiply by sqrt of trading days)
        annualized = std_dev * math.sqrt(252) * 100

        return round(annualized, 2)

    def _days_to_period(self, days: int) -> str:
        """Convert days to chart period string.

        Args:
            days: Number of days

        Returns:
            Period string (1m, 3m, 6m, 1y, 3y, 5y, 10y, 20y)
        """
        if days <= 30:
            return "1m"
        elif days <= 90:
            return "3m"
        elif days <= 180:
            return "6m"
        elif days <= 365:
            return "1y"
        elif days <= 1095:
            return "3y"
        elif days <= 1825:
            return "5y"
        elif days <= 3650:
            return "10y"
        else:
            return "20y"

    def get_batch_performance(self, codes: List[str]) -> Dict[str, Dict]:
        """Get performance metrics for multiple ETFs.

        Args:
            codes: List of ETF codes (max 50)

        Returns:
            Dictionary mapping ETF code to its performance metrics
        """
        result = {}
        for code in codes[:50]:  # Limit to 50 codes
            perf = self.get_performance(code)
            result[code] = perf.get("returns", {})
        return result
