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
        # キャッシュから一括取得（1回のDBクエリ）
        cached = self.get_batch_performance(codes)

        # キャッシュにない銘柄を特定（returnsが空 = キャッシュミス）
        missing_codes = [
            code for code in codes if not cached.get(code, {}).get("returns")
        ]

        # キャッシュミス時はフォールバック（従来の計算処理）
        fallback_data = {}
        for code in missing_codes:
            perf = self.get_performance(code)
            fallback_data[code] = {
                "returns": perf.get("returns", {}),
                "volatility": perf.get("volatility"),
            }

        performances = []
        for code in codes:
            if code in fallback_data:
                # フォールバックデータを使用
                perf = {
                    "code": code,
                    "returns": fallback_data[code]["returns"],
                    "volatility": fallback_data[code]["volatility"],
                }
            else:
                # キャッシュデータを使用
                cached_returns = cached.get(code, {})
                perf = {
                    "code": code,
                    "returns": cached_returns.get("returns", cached_returns),
                    "volatility": cached_returns.get("volatility"),
                }
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

    def _calculate_regression_return(self, code: str, days: int) -> Optional[float]:
        """Calculate regression-based return for a given period.

        Uses least squares method to fit a linear regression line (y = ax + b)
        and calculates the return based on the regression line endpoints.

        Args:
            code: ETF code
            days: Number of days to look back

        Returns:
            Regression return percentage or None if data unavailable
        """
        period = self._days_to_period(days)
        result = self.chart_service.get_chart_data(code, period)

        if not result or not result.get("data"):
            return None

        chart_data = result["data"]
        if len(chart_data) < 2:
            return None

        # Extract close prices
        prices = []
        for point in chart_data:
            close = point.get("close")
            if close is not None:
                prices.append(close)

        if len(prices) < 2:
            return None

        n = len(prices)
        # x values: 0, 1, 2, ..., n-1
        # Least squares: y = ax + b
        # a = (n * sum(xy) - sum(x) * sum(y)) / (n * sum(x^2) - sum(x)^2)
        # b = (sum(y) - a * sum(x)) / n

        sum_x = sum(range(n))  # 0 + 1 + ... + (n-1) = n*(n-1)/2
        sum_y = sum(prices)
        sum_xy = sum(i * prices[i] for i in range(n))
        sum_x2 = sum(i * i for i in range(n))  # 0^2 + 1^2 + ... + (n-1)^2

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return None

        a = (n * sum_xy - sum_x * sum_y) / denominator
        b = (sum_y - a * sum_x) / n

        # Regression line: start at x=0, end at x=n-1
        start_value = b  # y = a*0 + b = b
        end_value = a * (n - 1) + b  # y = a*(n-1) + b

        if start_value == 0:
            return None

        return ((end_value - start_value) / start_value) * 100

    def get_batch_performance(self, codes: List[str]) -> Dict[str, Dict]:
        """Get performance metrics for multiple ETFs from cache.

        Args:
            codes: List of ETF codes (max 50)

        Returns:
            Dictionary mapping ETF code to its performance metrics
            Example: {"1306": {"returns": {"1m": 2.5, ...}, "volatility": 15.2,
                               "regression": {"1m": 2.3, ...}}}
        """
        from src.models import PerformanceCache

        result = {}
        codes_limited = codes[:50]  # Limit to 50 codes

        # Fetch all cached data for the requested codes in one query
        cache_entries = PerformanceCache.query.filter(
            PerformanceCache.etf_code.in_(codes_limited)
        ).all()

        # Build lookup dict: {etf_code: {period: {return_rate, volatility, regression}}}
        cache_lookup: Dict[str, Dict] = {}
        for entry in cache_entries:
            if entry.etf_code not in cache_lookup:
                cache_lookup[entry.etf_code] = {
                    "returns": {},
                    "regression": {},
                    "volatility": None,
                }
            cache_lookup[entry.etf_code]["returns"][entry.period] = entry.return_rate
            cache_lookup[entry.etf_code]["regression"][
                entry.period
            ] = entry.regression_rate
            # volatility is stored once per code (typically in 1y period)
            if entry.volatility is not None:
                cache_lookup[entry.etf_code]["volatility"] = entry.volatility

        # Build result for each code (empty dict if no cache)
        for code in codes_limited:
            result[code] = cache_lookup.get(code, {})

        return result
