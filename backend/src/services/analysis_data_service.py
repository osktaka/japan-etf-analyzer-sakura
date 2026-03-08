"""Analysis data service for bulk portfolio analysis data retrieval."""
from datetime import date, timedelta
from typing import Dict, List

from src.models import (
    ETF,
    ETFTagRelation,
    PerformanceCache,
    PriceHistory,
    ScoreCache,
    Tag,
    db,
)


class AnalysisDataService:
    """Service for retrieving bulk analysis data for portfolio analysis."""

    def get_analysis_data(self, etf_codes: List[str]) -> Dict:
        """Get all analysis data for given ETF codes in a single call.

        Args:
            etf_codes: List of ETF codes to fetch data for

        Returns:
            Dictionary containing all analysis data sections
        """
        if not etf_codes:
            return self._empty_response()

        return {
            "performance_cache": self._get_performance_cache(etf_codes),
            "score_cache": self._get_score_cache(etf_codes),
            "etf_data": self._get_etf_data(etf_codes),
            "tag_data": self._get_tag_data(etf_codes),
            "price_data": self._get_price_data(etf_codes, months=13),
            "price_data_daily_30d": self._get_price_data_ohlcv(
                etf_codes, days=30
            ),
            "price_data_close_250d": self._get_price_data(
                etf_codes, months=14
            ),
        }

    def _get_performance_cache(self, codes: List[str]) -> List[Dict]:
        """Get performance cache data for given ETF codes."""
        rows = PerformanceCache.query.filter(
            PerformanceCache.etf_code.in_(codes)
        ).all()
        return [
            {
                "etf_code": r.etf_code,
                "period": r.period,
                "return_rate": r.return_rate,
                "volatility": r.volatility,
                "regression_rate": r.regression_rate,
            }
            for r in rows
        ]

    def _get_score_cache(self, codes: List[str]) -> List[Dict]:
        """Get score cache data for given ETF codes."""
        rows = ScoreCache.query.filter(
            ScoreCache.etf_code.in_(codes)
        ).all()
        return [
            {
                "etf_code": r.etf_code,
                "perspective": r.perspective,
                "total_score": r.total_score,
                "dividend_power": r.dividend_power,
                "cost_efficiency": r.cost_efficiency,
                "scale_reliability": r.scale_reliability,
                "trading_quality": r.trading_quality,
                "return_performance": r.return_performance,
            }
            for r in rows
        ]

    def _get_etf_data(self, codes: List[str]) -> List[Dict]:
        """Get ETF master data for given codes."""
        rows = ETF.query.filter(ETF.code.in_(codes)).all()
        return [
            {
                "code": r.code,
                "momentum_label": r.momentum_label,
                "manager": r.manager,
                "listing_date": (
                    r.listing_date.isoformat() if r.listing_date else None
                ),
                "deviation_rate": (
                    float(r.deviation_rate) if r.deviation_rate else None
                ),
            }
            for r in rows
        ]

    def _get_tag_data(self, codes: List[str]) -> List[Dict]:
        """Get tag data for given ETF codes."""
        rows = (
            db.session.query(
                ETFTagRelation.etf_code, Tag.name, Tag.category
            )
            .join(Tag, ETFTagRelation.tag_id == Tag.id)
            .filter(ETFTagRelation.etf_code.in_(codes))
            .all()
        )
        return [
            {"etf_code": r.etf_code, "name": r.name, "category": r.category}
            for r in rows
        ]

    def _get_price_data(self, codes: List[str], months: int) -> List[Dict]:
        """Get close price data for given period in months."""
        cutoff = date.today() - timedelta(days=months * 31)
        rows = (
            PriceHistory.query.filter(
                PriceHistory.etf_code.in_(codes),
                PriceHistory.date >= cutoff,
            )
            .order_by(PriceHistory.etf_code, PriceHistory.date)
            .all()
        )
        return [
            {
                "etf_code": r.etf_code,
                "date": r.date.strftime("%Y-%m-%d"),
                "close": r.close,
            }
            for r in rows
        ]

    def _get_price_data_ohlcv(
        self, codes: List[str], days: int
    ) -> List[Dict]:
        """Get OHLCV price data for given period in days."""
        cutoff = date.today() - timedelta(days=days)
        rows = (
            PriceHistory.query.filter(
                PriceHistory.etf_code.in_(codes),
                PriceHistory.date >= cutoff,
            )
            .order_by(PriceHistory.etf_code, PriceHistory.date)
            .all()
        )
        return [
            {
                "etf_code": r.etf_code,
                "date": r.date.strftime("%Y-%m-%d"),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]

    def _empty_response(self) -> Dict:
        """Return empty response structure."""
        return {
            "performance_cache": [],
            "score_cache": [],
            "etf_data": [],
            "tag_data": [],
            "price_data": [],
            "price_data_daily_30d": [],
            "price_data_close_250d": [],
        }
