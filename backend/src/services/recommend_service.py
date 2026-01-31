"""Recommendation service for ETF recommendations."""
from typing import Dict, List

from src.repositories import ETFRepository, ScoreCacheRepository

from .scoring_service import ScoringService


class RecommendService:
    """Service for ETF recommendation operations."""

    # Exclusion criteria
    EXCLUDE_KEYWORDS = [
        "レバレッジ",
        "インバース",
        "ダブル",
        "ベア",
        "2倍",
        "-2倍",
    ]
    MIN_AUM = 100_000_000  # 1億円 (minimum AUM to avoid delisting risk)

    PERSPECTIVES = [
        {
            "id": "balance",
            "name": "バランス",
            "description": "複数の観点でバランス良く評価された銘柄",
        },
        {
            "id": "dividend",
            "name": "配当収入",
            "description": "配当利回りが高く、定期的な配当収入を期待できる銘柄",
        },
        {
            "id": "low-cost",
            "name": "低コスト",
            "description": "信託報酬が低く、長期保有でコストを抑えられる銘柄",
        },
        {
            "id": "stability",
            "name": "安定性",
            "description": "純資産規模が大きく、安心して保有できる銘柄",
        },
        {
            "id": "volume",
            "name": "取引規模",
            "description": "出来高が多く、売買が成立しやすい銘柄",
        },
        {
            "id": "growth",
            "name": "成長性",
            "description": "過去の値上がり実績が良好な銘柄",
        },
    ]

    def __init__(self):
        """Initialize service with repositories."""
        self.etf_repository = ETFRepository()
        self.score_cache_repository = ScoreCacheRepository()
        self.scoring_service = ScoringService()

    def _is_excluded(self, etf) -> bool:
        """Check if ETF should be excluded from recommendations.

        Args:
            etf: ETF object to check

        Returns:
            True if ETF should be excluded
        """
        # Exclude leveraged/inverse ETFs
        if any(keyword in etf.name for keyword in self.EXCLUDE_KEYWORDS):
            return True

        # Exclude small AUM ETFs (delisting risk)
        if etf.total_assets and etf.total_assets < self.MIN_AUM:
            return True

        return False

    def get_perspectives(self) -> List[Dict]:
        """Get available recommendation perspectives."""
        return self.PERSPECTIVES

    def get_recommendations(
        self,
        perspective: str = "balance",
        limit: int = 5,
        scoring_mode: str = "full",
    ) -> Dict:
        """Get recommended ETFs based on perspective.

        Args:
            perspective: Recommendation perspective ID
            limit: Maximum number of recommendations
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Dictionary with perspective info and recommended ETFs with scores
        """
        perspective_info = next(
            (p for p in self.PERSPECTIVES if p["id"] == perspective),
            self.PERSPECTIVES[5],  # Default to balance
        )

        scored_items = self._get_scored_etfs_cached(perspective, limit, scoring_mode)

        return {
            "perspective": perspective_info,
            "items": [
                {
                    **item["etf"].to_summary_dict(),
                    "score": item["score"],
                    "axis_scores": item["axis_scores"],
                }
                for item in scored_items
            ],
        }

    def _get_scored_etfs_cached(self, perspective: str, limit: int, scoring_mode: str = "full") -> List[Dict]:
        """Get ETFs ranked by cached composite score.

        Args:
            perspective: Scoring perspective
            limit: Maximum number of results
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            List of dicts with ETF, score, and axis_scores, sorted by composite score
        """
        # Get top scored ETFs from cache (with buffer for exclusion filtering)
        cached_scores = self.score_cache_repository.get_scores_for_perspective(
            perspective, limit=limit * 3
        )

        # Get ETF details for cached scores
        result = []
        for cache in cached_scores:
            etf = self.etf_repository.get_by_code(cache.etf_code)
            if not etf:
                continue

            # Apply exclusion filters
            if self._is_excluded(etf):
                continue

            # Select score based on mode
            score = cache.total_score_full if scoring_mode == "full" else cache.total_score

            result.append(
                {
                    "etf": etf,
                    "score": score,
                    "axis_scores": {
                        "dividend_power": cache.dividend_power,
                        "cost_efficiency": cache.cost_efficiency,
                        "scale_reliability": cache.scale_reliability,
                        "trading_quality": cache.trading_quality,
                        "return_performance": cache.return_performance,
                    },
                }
            )

            if len(result) >= limit:
                break

        # Fallback: if cache is empty, calculate on-the-fly
        if not result:
            all_etfs = self.etf_repository.get_all()
            filtered_candidates = [
                etf for etf in all_etfs if not self._is_excluded(etf)
            ]
            scored = self.scoring_service.rank_etfs(
                filtered_candidates, perspective, limit
            )
            # Add empty axis_scores for compatibility
            for item in scored:
                item["axis_scores"] = {
                    "dividend_power": None,
                    "cost_efficiency": None,
                    "scale_reliability": None,
                    "trading_quality": None,
                    "return_performance": None,
                }
            return scored

        return result

    def _get_scored_etfs(self, perspective: str, limit: int) -> List[Dict]:
        """Get ETFs ranked by composite score (legacy method for backward compatibility).

        Args:
            perspective: Scoring perspective
            limit: Maximum number of results

        Returns:
            List of dicts with ETF and score, sorted by composite score
        """
        # Get all ETFs for percentile calculation across entire dataset
        all_etfs = self.etf_repository.get_all()

        # Apply exclusion filters (leverage/inverse and small AUM)
        filtered_candidates = [etf for etf in all_etfs if not self._is_excluded(etf)]

        # Rank by composite score
        return self.scoring_service.rank_etfs(filtered_candidates, perspective, limit)
