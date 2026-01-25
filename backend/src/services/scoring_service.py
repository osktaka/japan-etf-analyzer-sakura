"""Scoring service for ETF analysis and recommendations."""
import math
from typing import Dict, List, Optional

from src.models import ETF


class ScoringService:
    """Service for calculating ETF scores based on various criteria."""

    # Weight configurations for different perspectives
    WEIGHTS = {
        "high-dividend": {
            "dividend_yield": 0.7,  # Primary factor
            "total_assets": 0.3,  # Stability indicator
        },
        "low-cost": {
            "expense_ratio": 0.6,  # Primary factor (inverted)
            "total_assets": 0.4,  # Scale/reliability indicator
        },
        "beginner": {
            "total_assets": 0.4,  # Liquidity/reliability
            "expense_ratio": 0.3,  # Lower cost is better (inverted)
            "deviation_rate": 0.3,  # Lower deviation is better (inverted)
        },
    }

    def calculate_score(self, etf: ETF, perspective: str) -> float:
        """Calculate composite score for an ETF based on perspective.

        Args:
            etf: ETF object to score
            perspective: Scoring perspective (high-dividend, low-cost, beginner)

        Returns:
            Composite score (0-100)
        """
        if perspective not in self.WEIGHTS:
            return 0.0

        weights = self.WEIGHTS[perspective]
        score = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            metric_score = self._get_metric_score(etf, metric, perspective)
            if metric_score is not None:
                score += metric_score * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return (score / total_weight) * 100

    def _get_metric_score(
        self, etf: ETF, metric: str, perspective: str
    ) -> Optional[float]:
        """Get normalized score for a specific metric.

        Args:
            etf: ETF object
            metric: Metric name
            perspective: Current perspective for context

        Returns:
            Normalized score (0-1) or None if data unavailable
        """
        if metric == "dividend_yield":
            if etf.dividend_yield is None:
                return None
            # Normalize: higher is better, cap at 10%
            return min(float(etf.dividend_yield) / 10.0, 1.0)

        elif metric == "expense_ratio":
            if etf.expense_ratio is None:
                return None
            # Invert: lower is better, normalize (0.01% = best, 1% = worst)
            ratio = float(etf.expense_ratio)
            return max(0.0, 1.0 - (ratio / 1.0))

        elif metric == "total_assets":
            if etf.total_assets is None:
                return None
            # Normalize: log scale, larger is better
            # 10B yen = 0.5, 100B yen = 0.75, 1T yen = 1.0
            assets = float(etf.total_assets)
            if assets <= 0:
                return 0.0
            log_assets = math.log10(assets)
            # Normalize: 8 (100M) = 0, 12 (1T) = 1
            return min(max((log_assets - 8) / 4, 0.0), 1.0)

        elif metric == "deviation_rate":
            if etf.deviation_rate is None:
                return None
            # Invert: lower absolute deviation is better
            deviation = abs(float(etf.deviation_rate))
            # 0% deviation = 1.0, 5% deviation = 0
            return max(0.0, 1.0 - (deviation / 5.0))

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
