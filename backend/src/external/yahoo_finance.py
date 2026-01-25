"""Yahoo Finance API client for chart data."""
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _is_mock_mode() -> bool:
    """Check if mock mode is enabled."""
    return os.environ.get("USE_MOCK_DATA", "true").lower() == "true"


class YahooFinanceClient:
    """Client for fetching data from Yahoo Finance."""

    PERIOD_DAYS = {
        "1w": 7,
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "3y": 1095,
    }

    @staticmethod
    def get_chart_data(code: str, period: str = "1m") -> List[Dict]:
        """Get historical price data for an ETF.

        Args:
            code: ETF code (e.g., "1306")
            period: Time period ("1w", "1m", "3m", "6m", "1y", "3y")

        Returns:
            List of price data dictionaries
        """
        days = YahooFinanceClient.PERIOD_DAYS.get(period, 30)

        if _is_mock_mode():
            return YahooFinanceClient._generate_mock_data(code, days)

        # 本番モード: yfinanceでデータ取得
        try:
            return YahooFinanceClient._fetch_from_yfinance(code, days)
        except Exception as e:
            logger.warning(f"yfinance fetch failed for {code}: {e}")
            # DBキャッシュからフォールバック
            cached = YahooFinanceClient._get_from_cache(code, days)
            if cached:
                logger.info(f"Using cached data for {code}")
                return cached
            # キャッシュもない場合はモックデータ
            logger.warning(f"No cache available for {code}, using mock")
            return YahooFinanceClient._generate_mock_data(code, days)

    @staticmethod
    def _fetch_from_yfinance(code: str, days: int) -> List[Dict]:
        """Fetch real data from Yahoo Finance using yfinance."""
        import yfinance as yf

        ticker = f"{code}.T"  # 東証ティッカー形式
        stock = yf.Ticker(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)

        df = stock.history(start=start_date, end=end_date)
        if df.empty:
            raise ValueError(f"No data returned for {ticker}")

        data = []
        for date, row in df.iterrows():
            data.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                }
            )

        # DBキャッシュに保存
        YahooFinanceClient._save_to_cache(code, data)
        return data[-days:] if len(data) > days else data

    @staticmethod
    def _get_from_cache(code: str, days: int) -> Optional[List[Dict]]:
        """Get cached data from database."""
        try:
            from src.models import PriceHistory

            cutoff = datetime.now().date() - timedelta(days=days)
            records = (
                PriceHistory.query.filter(
                    PriceHistory.etf_code == code,
                    PriceHistory.date >= cutoff,
                )
                .order_by(PriceHistory.date)
                .all()
            )
            if not records:
                return None
            return [r.to_dict() for r in records]
        except Exception as e:
            logger.warning(f"Cache read failed for {code}: {e}")
            return None

    @staticmethod
    def _save_to_cache(code: str, data: List[Dict]) -> None:
        """Save data to database cache."""
        try:
            from src.models import PriceHistory, db

            for item in data:
                date = datetime.strptime(item["date"], "%Y-%m-%d").date()
                existing = PriceHistory.query.filter_by(
                    etf_code=code, date=date
                ).first()

                if existing:
                    existing.open = item["open"]
                    existing.high = item["high"]
                    existing.low = item["low"]
                    existing.close = item["close"]
                    existing.volume = item["volume"]
                    existing.updated_at = datetime.utcnow()
                else:
                    record = PriceHistory(
                        etf_code=code,
                        date=date,
                        open=item["open"],
                        high=item["high"],
                        low=item["low"],
                        close=item["close"],
                        volume=item["volume"],
                    )
                    db.session.add(record)

            db.session.commit()
        except Exception as e:
            logger.warning(f"Cache save failed for {code}: {e}")

    @staticmethod
    def get_current_price(code: str) -> Optional[Dict]:
        """Get current price data for an ETF."""
        if _is_mock_mode():
            return YahooFinanceClient._get_mock_current_price(code)

        try:
            import yfinance as yf

            ticker = f"{code}.T"
            stock = yf.Ticker(ticker)
            info = stock.info

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev_close = info.get("regularMarketPreviousClose") or info.get(
                "previousClose"
            )

            if price is None:
                # historyから最新価格を取得
                df = stock.history(period="1d")
                if df.empty:
                    raise ValueError(f"No price data for {ticker}")
                price = float(df["Close"].iloc[-1])
                prev_close = price  # 差分計算不可

            change = price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            return {
                "code": code,
                "price": round(float(price), 2),
                "change": round(float(change), 2),
                "change_percent": round(float(change_pct), 2),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Current price fetch failed for {code}: {e}")
            return YahooFinanceClient._get_mock_current_price(code)

    @staticmethod
    def _get_mock_current_price(code: str) -> Optional[Dict]:
        """Get mock current price."""
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

        price = base_prices.get(code, 10000)
        change = random.uniform(-0.02, 0.02)
        current_price = price * (1 + change)

        return {
            "code": code,
            "price": round(current_price, 2),
            "change": round(current_price - price, 2),
            "change_percent": round(change * 100, 2),
            "timestamp": datetime.now().isoformat(),
        }

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

        for _ in range(days):
            change = random.uniform(-0.02, 0.025)
            price = price * (1 + change)

            high = price * (1 + random.uniform(0.005, 0.015))
            low = price * (1 - random.uniform(0.005, 0.015))
            open_price = price * (1 + random.uniform(-0.01, 0.01))

            data.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "open": round(open_price, 2),
                    "high": round(high, 2),
                    "low": round(low, 2),
                    "close": round(price, 2),
                    "volume": random.randint(100000, 1000000),
                }
            )

            current_date += timedelta(days=1)
            while current_date.weekday() >= 5:
                current_date += timedelta(days=1)

        return data
