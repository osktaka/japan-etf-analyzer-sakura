"""Scoring service for ETF analysis and recommendations."""
import math
from typing import Dict, List, Optional

from src.models import ETF
from src.repositories import ETFRepository


class ScoringService:
    """Service for calculating ETF scores based on unified 5-axis evaluation."""

    # Unified weight configurations for 6 perspectives
    # Each perspective weights: dividend_power, cost_efficiency, scale, trading_quality, return_performance
    WEIGHTS = {
        "dividend": {
            "dividend_power": 0.5,
            "cost_efficiency": 0.1,
            "scale_reliability": 0.2,
            "trading_quality": 0.1,
            "return_performance": 0.1,
        },
        "low-cost": {
            "dividend_power": 0.1,
            "cost_efficiency": 0.5,
            "scale_reliability": 0.2,
            "trading_quality": 0.1,
            "return_performance": 0.1,
        },
        "stability": {
            "dividend_power": 0.1,
            "cost_efficiency": 0.2,
            "scale_reliability": 0.4,
            "trading_quality": 0.2,
            "return_performance": 0.1,
        },
        "volume": {
            "dividend_power": 0.1,
            "cost_efficiency": 0.1,
            "scale_reliability": 0.2,
            "trading_quality": 0.5,
            "return_performance": 0.1,
        },
        "growth": {
            "dividend_power": 0.1,
            "cost_efficiency": 0.1,
            "scale_reliability": 0.2,
            "trading_quality": 0.1,
            "return_performance": 0.5,
        },
        "balance": {
            "dividend_power": 0.2,
            "cost_efficiency": 0.2,
            "scale_reliability": 0.2,
            "trading_quality": 0.2,
            "return_performance": 0.2,
        },
    }

    def __init__(self):
        """Initialize service with repository."""
        self.etf_repository = ETFRepository()

    def calculate_score(self, etf: ETF, perspective: str) -> float:
        """Calculate composite score for an ETF based on perspective.

        Args:
            etf: ETF object to score
            perspective: Scoring perspective (dividend, low-cost, stability, volume, growth, balance)

        Returns:
            Composite score (0-100)
        """
        if perspective not in self.WEIGHTS:
            return 0.0

        weights = self.WEIGHTS[perspective]
        score = 0.0
        total_weight = 0.0

        for axis, weight in weights.items():
            axis_score = self._get_axis_score(etf, axis)
            if axis_score is not None:
                score += axis_score * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return (score / total_weight) * 100

    def _get_axis_score(self, etf: ETF, axis: str) -> Optional[float]:
        """Get normalized score for a specific evaluation axis.

        Args:
            etf: ETF object
            axis: Axis name (dividend_power, cost_efficiency, scale_reliability, trading_quality, return_performance)

        Returns:
            Normalized score (0-1) or None if data unavailable
        """
        if axis == "dividend_power":
            return self._score_dividend_power(etf)
        elif axis == "cost_efficiency":
            return self._score_cost_efficiency(etf)
        elif axis == "scale_reliability":
            return self._score_scale_reliability(etf)
        elif axis == "trading_quality":
            return self._score_trading_quality(etf)
        elif axis == "return_performance":
            return self._score_return_performance(etf)
        return None

    def _score_dividend_power(self, etf: ETF) -> Optional[float]:
        """Score dividend power (配当力).

        Metric: dividend_yield
        Normalization: min(dividend_yield / 10.0, 1.0)
        """
        if etf.dividend_yield is None:
            return None
        return min(float(etf.dividend_yield) / 10.0, 1.0)

    def _score_cost_efficiency(self, etf: ETF) -> Optional[float]:
        """Score cost efficiency (コスト効率).

        Metric: expense_ratio
        Normalization: max(0.0, 1.0 - expense_ratio / 1.0)
        Lower is better (inverted)
        """
        if etf.expense_ratio is None:
            return None
        ratio = float(etf.expense_ratio)
        return max(0.0, 1.0 - (ratio / 1.0))

    def _score_scale_reliability(self, etf: ETF) -> Optional[float]:
        """Score scale and reliability (規模・信頼性).

        Metric: total_assets
        Normalization: (log10(assets) - 8) / 4, capped at [0, 1]
        Log scale: 10^8 (100M) = 0, 10^12 (1T) = 1
        """
        if etf.total_assets is None:
            return None
        assets = float(etf.total_assets)
        if assets <= 0:
            return 0.0
        log_assets = math.log10(assets)
        return min(max((log_assets - 8) / 4, 0.0), 1.0)

    def _score_trading_quality(self, etf: ETF) -> Optional[float]:
        """Score trading quality (取引品質).

        Metrics:
        - average_volume (30-day moving average)
        - deviation_rate (absolute value)

        Weighted: volume 70%, deviation 30%
        """
        avg_volume = self.etf_repository.get_average_volume(etf.code)
        deviation = etf.deviation_rate

        volume_score = None
        deviation_score = None

        # Volume score (log scale: 10^3 = 0, 10^6 = 1)
        if avg_volume is not None and avg_volume > 0:
            log_volume = math.log10(avg_volume)
            volume_score = min(max((log_volume - 3) / 3, 0.0), 1.0)

        # Deviation score (lower is better: 0% = 1.0, 5% = 0)
        if deviation is not None:
            deviation_abs = abs(float(deviation))
            deviation_score = max(0.0, 1.0 - (deviation_abs / 5.0))

        # Weighted average (if both available)
        if volume_score is not None and deviation_score is not None:
            return volume_score * 0.7 + deviation_score * 0.3
        elif volume_score is not None:
            return volume_score
        elif deviation_score is not None:
            return deviation_score
        return None

    def _score_return_performance(self, etf: ETF) -> Optional[float]:
        """Score return performance (リターン実績).

        Metrics:
        - return_1y
        - return_3y

        Normalization: (return_rate + 50) / 150
        Range: -50% to +100% mapped to 0-1
        Weighted: 1y 40%, 3y 60%
        """
        return_rates = self.etf_repository.get_return_rates(etf.code)
        return_1y = return_rates.get("1y")
        return_3y = return_rates.get("3y")

        score_1y = None
        score_3y = None

        if return_1y is not None:
            score_1y = (return_1y + 50) / 150
            score_1y = max(0.0, min(1.0, score_1y))

        if return_3y is not None:
            score_3y = (return_3y + 50) / 150
            score_3y = max(0.0, min(1.0, score_3y))

        # Weighted average
        if score_1y is not None and score_3y is not None:
            return score_1y * 0.4 + score_3y * 0.6
        elif score_1y is not None:
            return score_1y
        elif score_3y is not None:
            return score_3y
        return None

    def rank_etfs(
        self, etfs: List[ETF], perspective: str, limit: int = 10
    ) -> List[Dict]:
        """Rank ETFs by composite score for a perspective.

        Args:
            etfs: List of ETF objects to rank
            perspective: Scoring perspective
            limit: Maximum number of results

        Returns:
            List of dicts with ETF and score, sorted by score descending
        """
        scored = []
        for etf in etfs:
            score = self.calculate_score(etf, perspective)
            if score > 0:
                scored.append({"etf": etf, "score": score})

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]
