"""Scoring service for ETF analysis and recommendations."""
import math
from typing import Dict, List, Optional

from src.models import ETF
from src.repositories import ETFRepository


class ScoringService:
    """Service for calculating ETF scores based on unified 5-axis evaluation."""

    # Minimum required axes for scoring (out of 5 axes)
    MIN_REQUIRED_AXES = 3

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
        self._avg_volumes_cache = {}
        self._return_rates_cache = {}

    def _percentile_score(
        self, value: Optional[float], values: List[float], inverted: bool = False
    ) -> Optional[float]:
        """Calculate percentile-based score (0-1).

        Args:
            value: Target value to score
            values: List of all values for comparison
            inverted: If True, lower values get higher scores (for costs)

        Returns:
            Percentile score (0-1) or None if data unavailable
        """
        if value is None:
            return None

        # Filter out None values
        sorted_vals = sorted([v for v in values if v is not None])
        if not sorted_vals:
            return None

        # Calculate rank (number of values <= target value)
        rank = sum(1 for v in sorted_vals if v <= value)

        # Convert to percentile (0-1)
        score = (rank - 1) / max(len(sorted_vals) - 1, 1)

        # Invert if needed (for cost metrics where lower is better)
        return 1 - score if inverted else score

    def calculate_score(self, etf: ETF, perspective: str) -> float:
        """Calculate composite score for an ETF based on perspective.

        Args:
            etf: ETF object to score
            perspective: Scoring perspective (dividend, low-cost, stability, volume, growth, balance)

        Returns:
            Composite score (0-100), or 0 if insufficient data (< 3 axes)
        """
        if perspective not in self.WEIGHTS:
            return 0.0

        weights = self.WEIGHTS[perspective]
        score = 0.0
        total_weight = 0.0
        available_axes = 0

        for axis, weight in weights.items():
            axis_score = self._get_axis_score(etf, axis)
            if axis_score is not None:
                score += axis_score * weight
                total_weight += weight
                available_axes += 1

        # Require minimum number of axes for scoring
        if available_axes < self.MIN_REQUIRED_AXES:
            return 0.0

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
        Normalization: Percentile-based (higher is better)
        """
        if etf.dividend_yield is None:
            return None
        return self._percentile_score(
            float(etf.dividend_yield), self._dividend_yields, inverted=False
        )

    def _score_cost_efficiency(self, etf: ETF) -> Optional[float]:
        """Score cost efficiency (コスト効率).

        Metric: expense_ratio
        Normalization: Percentile-based (lower is better, inverted)
        """
        if etf.expense_ratio is None:
            return None
        return self._percentile_score(
            float(etf.expense_ratio), self._expense_ratios, inverted=True
        )

    def _score_scale_reliability(self, etf: ETF) -> Optional[float]:
        """Score scale and reliability (規模・信頼性).

        Metric: total_assets
        Normalization: Percentile-based (higher is better)
        """
        if etf.total_assets is None:
            return None
        return self._percentile_score(
            float(etf.total_assets), self._total_assets, inverted=False
        )

    def _score_trading_quality(self, etf: ETF) -> Optional[float]:
        """Score trading quality (取引品質).

        Metrics:
        - trading_value (price * average_volume) - 50%
        - average_volume (30-day moving average) - 30%
        - deviation_rate (absolute value) - 20%

        All metrics use percentile normalization
        """
        # Use cached data if available, otherwise fetch directly
        avg_volume = self._avg_volumes_cache.get(etf.code)
        if avg_volume is None and not self._avg_volumes_cache:
            avg_volume = self.etf_repository.get_average_volume(etf.code)
        deviation = etf.deviation_rate

        trading_value_score = None
        volume_score = None
        deviation_score = None

        # Trading value score (price * volume)
        if avg_volume is not None and etf.market_price is not None:
            trading_value = float(etf.market_price) * avg_volume
            trading_value_score = self._percentile_score(
                trading_value, self._trading_values, inverted=False
            )

        # Volume score (percentile-based)
        if avg_volume is not None:
            volume_score = self._percentile_score(
                avg_volume, self._avg_volumes, inverted=False
            )

        # Deviation score (lower is better)
        if deviation is not None:
            deviation_abs = abs(float(deviation))
            deviation_score = self._percentile_score(
                deviation_abs, self._deviation_rates, inverted=True
            )

        # Weighted average
        scores = []
        weights = []
        if trading_value_score is not None:
            scores.append(trading_value_score)
            weights.append(0.5)
        if volume_score is not None:
            scores.append(volume_score)
            weights.append(0.3)
        if deviation_score is not None:
            scores.append(deviation_score)
            weights.append(0.2)

        if not scores:
            return None

        # Normalize weights
        total_weight = sum(weights)
        return sum(s * w for s, w in zip(scores, weights)) / total_weight

    def _score_return_performance(self, etf: ETF) -> Optional[float]:
        """Score return performance (リターン実績).

        Metrics:
        - return_1y - 40%
        - return_3y - 60%

        Normalization: Percentile-based (higher is better)
        """
        # Use cached data if available, otherwise fetch directly
        return_rates = self._return_rates_cache.get(etf.code)
        if return_rates is None and not self._return_rates_cache:
            return_rates = self.etf_repository.get_return_rates(etf.code)
        else:
            return_rates = return_rates or {"1y": None, "3y": None}

        return_1y = return_rates.get("1y")
        return_3y = return_rates.get("3y")

        score_1y = None
        score_3y = None

        if return_1y is not None:
            score_1y = self._percentile_score(
                return_1y, self._return_1y, inverted=False
            )

        if return_3y is not None:
            score_3y = self._percentile_score(
                return_3y, self._return_3y, inverted=False
            )

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
        # Batch fetch data and cache for individual scoring
        etf_codes = [etf.code for etf in etfs]
        self._avg_volumes_cache = self.etf_repository.get_average_volumes_batch(etf_codes)
        self._return_rates_cache = self.etf_repository.get_return_rates_batch(etf_codes)

        # Collect values for percentile calculation
        self._collect_percentile_data(etfs)

        scored = []
        for etf in etfs:
            score = self.calculate_score(etf, perspective)
            if score > 0:
                scored.append({"etf": etf, "score": score})

        # Clear cache after scoring
        self._avg_volumes_cache = {}
        self._return_rates_cache = {}

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def get_all_scores_batch(self, etf_codes: List[str]) -> Dict[str, Dict[str, float]]:
        """Get all 6 perspective scores for multiple ETFs.

        Args:
            etf_codes: List of ETF codes

        Returns:
            Dict mapping ETF code to dict of perspective scores
            Example: {"1489": {"balance": 78.5, "dividend": 85.2, ...}}
        """
        etfs = [self.etf_repository.get_by_code(code) for code in etf_codes]
        etfs = [etf for etf in etfs if etf]

        if not etfs:
            return {}

        # Batch fetch data
        self._avg_volumes_cache = self.etf_repository.get_average_volumes_batch(etf_codes)
        self._return_rates_cache = self.etf_repository.get_return_rates_batch(etf_codes)
        self._collect_percentile_data(etfs)

        result = {}
        perspectives = ["balance", "dividend", "low-cost", "stability", "volume", "growth"]

        for etf in etfs:
            scores = {}
            for perspective in perspectives:
                score = self.calculate_score(etf, perspective)
                scores[perspective] = round(score, 1)
            result[etf.code] = scores

        # Clear cache
        self._avg_volumes_cache = {}
        self._return_rates_cache = {}

        return result

    def _collect_percentile_data(self, etfs: List[ETF]) -> None:
        """Collect values from all ETFs for percentile calculation.

        Args:
            etfs: List of ETF objects
        """
        self._dividend_yields = [etf.dividend_yield for etf in etfs if etf.dividend_yield is not None]
        self._expense_ratios = [etf.expense_ratio for etf in etfs if etf.expense_ratio is not None]
        self._total_assets = [etf.total_assets for etf in etfs if etf.total_assets is not None]

        # Use cached data (already fetched in rank_etfs)
        self._avg_volumes = [vol for vol in self._avg_volumes_cache.values() if vol is not None]

        # Collect trading value (price * volume)
        self._trading_values = []
        for etf in etfs:
            avg_volume = self._avg_volumes_cache.get(etf.code)
            if avg_volume is not None and etf.market_price is not None:
                trading_value = float(etf.market_price) * avg_volume
                self._trading_values.append(trading_value)

        # Collect deviation rates
        self._deviation_rates = [abs(float(etf.deviation_rate)) for etf in etfs if etf.deviation_rate is not None]

        # Use cached return rates (already fetched in rank_etfs)
        self._return_1y = []
        self._return_3y = []
        for etf_code, return_rates in self._return_rates_cache.items():
            if return_rates.get("1y") is not None:
                self._return_1y.append(return_rates["1y"])
            if return_rates.get("3y") is not None:
                self._return_3y.append(return_rates["3y"])
