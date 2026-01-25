"""Recommendation service for ETF recommendations."""
from typing import Dict, List

from src.repositories import ETFRepository, TagRepository

from .scoring_service import ScoringService


class RecommendService:
    """Service for ETF recommendation operations."""

    PERSPECTIVES = [
        {
            "id": "high-dividend",
            "name": "高配当",
            "description": "配当利回りと安定性を考慮したおすすめ",
        },
        {
            "id": "low-cost",
            "name": "低コスト",
            "description": "信託報酬と純資産規模を考慮したおすすめ",
        },
        {
            "id": "beginner",
            "name": "初心者向け",
            "description": "低リスク・高流動性のおすすめETF",
        },
        {
            "id": "diversified",
            "name": "分散投資",
            "description": "幅広い銘柄に分散投資できるETF",
        },
        {
            "id": "popular",
            "name": "人気",
            "description": "取引量が多い人気のETF",
        },
    ]

    # Perspectives that use composite scoring
    SCORED_PERSPECTIVES = {"high-dividend", "low-cost", "beginner"}

    def __init__(self):
        """Initialize service with repositories."""
        self.etf_repository = ETFRepository()
        self.tag_repository = TagRepository()
        self.scoring_service = ScoringService()

    def get_perspectives(self) -> List[Dict]:
        """Get available recommendation perspectives."""
        return self.PERSPECTIVES

    def get_recommendations(
        self,
        perspective: str = "popular",
        limit: int = 5,
    ) -> Dict:
        """Get recommended ETFs based on perspective.

        Args:
            perspective: Recommendation perspective ID
            limit: Maximum number of recommendations

        Returns:
            Dictionary with perspective info and recommended ETFs
        """
        perspective_info = next(
            (p for p in self.PERSPECTIVES if p["id"] == perspective),
            self.PERSPECTIVES[4],
        )

        etfs = self._get_etfs_by_perspective(perspective, limit)

        return {
            "perspective": perspective_info,
            "items": [etf.to_summary_dict() for etf in etfs],
        }

    def _get_etfs_by_perspective(self, perspective: str, limit: int) -> List:
        """Get ETFs based on perspective."""
        # Use composite scoring for specific perspectives
        if perspective in self.SCORED_PERSPECTIVES:
            return self._get_scored_etfs(perspective, limit)

        # Tag-based recommendations for other perspectives
        if perspective in ("diversified", "popular"):
            tag_name_map = {
                "diversified": "分散投資",
                "popular": "人気",
            }
            tag_name = tag_name_map.get(perspective, "人気")
            tag = self.tag_repository.get_by_name(tag_name)
            if tag:
                return self.etf_repository.get_by_tag(tag.id)[:limit]
            return []

        return self.etf_repository.search(limit=limit)

    def _get_scored_etfs(self, perspective: str, limit: int) -> List:
        """Get ETFs ranked by composite score.

        Args:
            perspective: Scoring perspective
            limit: Maximum number of results

        Returns:
            List of ETFs sorted by composite score
        """
        # Get candidate ETFs based on perspective
        if perspective == "high-dividend":
            # Get ETFs with dividend data
            candidates = self.etf_repository.get_high_dividend(limit * 3)
        elif perspective == "low-cost":
            # Get ETFs with expense ratio data
            candidates = self.etf_repository.get_low_cost(limit * 3)
        else:
            # Get all ETFs for beginner perspective
            candidates = self.etf_repository.search(limit=limit * 3)

        # Rank by composite score
        ranked = self.scoring_service.rank_etfs(candidates, perspective, limit)
        return [item["etf"] for item in ranked]
