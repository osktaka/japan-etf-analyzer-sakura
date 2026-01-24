"""Yahoo Finance API client for chart data."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random


class YahooFinanceClient:
    """Client for fetching data from Yahoo Finance."""

    @staticmethod
    def get_chart_data(
        code: str,
        period: str = "1m",
    ) -> List[Dict]:
        """Get historical price data for an ETF.

        Args:
            code: ETF code (e.g., "1306")
            period: Time period ("1w", "1m", "3m", "6m", "1y", "3y")

        Returns:
            List of price data dictionaries
        """
        days = {
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "3y": 1095,
        }.get(period, 30)

        return YahooFinanceClient._generate_mock_data(code, days)

    @staticmethod
    def _generate_mock_data(code: str, days: int) -> List[Dict]:
        """Generate mock chart data for development."""
        base_prices = {
            "1306": 2500,
            "1321": 30500,
            "1343": 1850,
            "1550": 4200,
            "2558": 18500,
            "1476": 1950,
            "1489": 52000,
            "2559": 17800,
        }

        base_price = base_prices.get(code, 10000)
        data = []
        current_date = datetime.now() - timedelta(days=days)
        price = base_price

        for i in range(days):
            change = random.uniform(-0.02, 0.025)
            price = price * (1 + change)

            high = price * (1 + random.uniform(0.005, 0.015))
            low = price * (1 - random.uniform(0.005, 0.015))
            open_price = price * (1 + random.uniform(-0.01, 0.01))

            data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(price, 2),
                "volume": random.randint(100000, 1000000),
            })

            current_date += timedelta(days=1)
            while current_date.weekday() >= 5:
                current_date += timedelta(days=1)

        return data

    @staticmethod
    def get_current_price(code: str) -> Optional[Dict]:
        """Get current price data for an ETF."""
        base_prices = {
            "1306": 2505,
            "1321": 30500,
            "1343": 1850,
            "1550": 4200,
            "2558": 18500,
            "1476": 1950,
            "1489": 52000,
            "2559": 17800,
        }

        price = base_prices.get(code)
        if not price:
            return None

        change = random.uniform(-0.02, 0.02)
        current_price = price * (1 + change)

        return {
            "code": code,
            "price": round(current_price, 2),
            "change": round(current_price - price, 2),
            "change_percent": round(change * 100, 2),
            "timestamp": datetime.now().isoformat(),
        }
