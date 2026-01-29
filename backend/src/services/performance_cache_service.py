"""Performance cache recalculation service."""
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.repositories.stock_split_repository import StockSplitRepository
from src.services.chart_service import ChartService

# Add scripts to path
scripts_path = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

# Import calculation functions from update_etf_data script
from update_etf_data import (  # noqa: E402
    PERIODS,
    calculate_regression_return_from_df,
    calculate_return_from_df,
    calculate_volatility_from_df,
)


class PerformanceCacheService:
    """Service for recalculating performance cache with split adjustments."""

    def __init__(self):
        """Initialize service."""
        self.chart_service = ChartService()
        self.stock_split_repo = StockSplitRepository()

    def recalculate_for_split(self, split_id: int) -> Optional[dict]:
        """Recalculate performance cache for an ETF with split adjustments.

        Args:
            split_id: Stock split ID

        Returns:
            Dictionary with etf_code and updated_periods, or None if split not found
        """
        from src.models import PerformanceCache, db

        # Get the stock split
        split = self.stock_split_repo.get_by_id(split_id)
        if not split:
            return None

        etf_code = split.etf_code

        # Get all periods defined in update_etf_data.py
        periods = list(PERIODS.keys())

        # Get split-adjusted chart data for all periods
        batch_data = self.chart_service.get_batch_periods_chart_data(etf_code, periods)
        if not batch_data:
            return None

        # Convert each period's chart data to DataFrame and calculate metrics
        updated_periods = []
        for period_id, days in PERIODS.items():
            chart_data = batch_data["charts"].get(period_id, [])
            if not chart_data:
                continue

            # Convert chart data to DataFrame
            df = self._chart_data_to_dataframe(chart_data)
            if df.empty:
                continue

            # Calculate metrics
            return_rate = calculate_return_from_df(df, days)
            regression_rate = calculate_regression_return_from_df(df, days)
            volatility = (
                calculate_volatility_from_df(df, 365) if period_id == "1y" else None
            )

            # UPSERT to PerformanceCache
            existing = PerformanceCache.query.filter_by(
                etf_code=etf_code, period=period_id
            ).first()

            if existing:
                existing.return_rate = return_rate
                existing.regression_rate = regression_rate
                existing.volatility = volatility
                existing.calculated_at = datetime.utcnow()
            else:
                cache = PerformanceCache(
                    etf_code=etf_code,
                    period=period_id,
                    return_rate=return_rate,
                    regression_rate=regression_rate,
                    volatility=volatility,
                    calculated_at=datetime.utcnow(),
                )
                db.session.add(cache)

            updated_periods.append(period_id)

        db.session.commit()

        return {
            "etf_code": etf_code,
            "updated_periods": updated_periods,
        }

    def _chart_data_to_dataframe(self, chart_data: List[dict]) -> pd.DataFrame:
        """Convert chart data to pandas DataFrame.

        Args:
            chart_data: List of chart data points with date, open, high, low, close, volume

        Returns:
            DataFrame with date index and OHLCV columns
        """
        if not chart_data:
            return pd.DataFrame()

        # Extract data
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        for point in chart_data:
            date_str = point.get("date")
            if not date_str:
                continue

            # Parse date
            date = pd.to_datetime(date_str)
            dates.append(date)

            # Extract OHLCV
            opens.append(point.get("open"))
            highs.append(point.get("high"))
            lows.append(point.get("low"))
            closes.append(point.get("close"))
            volumes.append(point.get("volume", 0))

        if not dates:
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(
            {
                "Open": opens,
                "High": highs,
                "Low": lows,
                "Close": closes,
                "Volume": volumes,
            },
            index=dates,
        )

        # Sort by date
        df.sort_index(inplace=True)

        return df
