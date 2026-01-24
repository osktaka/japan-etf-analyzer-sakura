"""Recommendation service for ETF recommendations."""
from typing import Dict, List, Optional

from src.repositories import ETFRepository, TagRepository


class RecommendService:
    """Service for ETF recommendation operations."""

    PERSPECTIVES = [
        {
            "id": "high-dividend",
            "name": "高配当",
            "description": "配当利回りが高いETFをおすすめ",
        },
        {
            "id": "low-cost",
            "name": "低コスト",
            "description": "信託報酬が低いETFをおすすめ",
        },
        {
            "id": "beginner",
            "name": "初心者向け",
            "description": "投資初心者におすすめのETF",
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

    def __init__(self):
        """Initialize service with repositories."""
        self.etf_repository = ETFRepository()
        self.tag_repository = TagRepository()

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
        if perspective == "high-dividend":
            return self.etf_repository.get_high_dividend(limit)

        elif perspective == "low-cost":
            return self.etf_repository.get_low_cost(limit)

        elif perspective in ("beginner", "diversified", "popular"):
            tag_name_map = {
                "beginner": "初心者向け",
                "diversified": "分散投資",
                "popular": "人気",
            }
            tag_name = tag_name_map.get(perspective, "人気")
            tag = self.tag_repository.get_by_name(tag_name)
            if tag:
                return self.etf_repository.get_by_tag(tag.id)[:limit]
            return []

        return self.etf_repository.search(limit=limit)
