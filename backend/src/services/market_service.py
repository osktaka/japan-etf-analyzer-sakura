"""Market analysis service for tag-momentum cross-tabulation."""
from collections import defaultdict
from typing import Dict, Optional

from sqlalchemy import func

from src.models import ETF, ETFTagRelation, Tag, db

# Momentum label to score mapping
MOMENTUM_SCORES = {
    "上昇加速": 100,
    "上昇維持": 85,
    "上昇減速": 70,
    "反転上昇": 60,
    "失速": 40,
    "下降減速": 30,
    "下降維持": 15,
    "下降加速": 0,
}

NEUTRAL_SCORE = 50


class MarketService:
    """Service for market analysis operations."""

    def get_tag_momentum(self, category: Optional[str] = None) -> Dict:
        """Get tag-momentum cross-tabulation data.

        Args:
            category: Optional tag category filter

        Returns:
            Dictionary with tags, categories, and total_etf_count
        """
        query = (
            db.session.query(
                Tag.id,
                Tag.name,
                Tag.color,
                Tag.category,
                ETF.momentum_label,
                func.count(ETF.code).label("count"),
            )
            .join(ETFTagRelation, Tag.id == ETFTagRelation.tag_id)
            .join(ETF, ETFTagRelation.etf_code == ETF.code)
        )

        if category:
            query = query.filter(Tag.category == category)

        rows = query.group_by(Tag.id, ETF.momentum_label).all()

        # Aggregate by tag
        tag_map = defaultdict(lambda: {
            "momentum_distribution": defaultdict(int),
            "etf_count": 0,
        })
        tag_info = {}

        for tag_id, name, color, cat, momentum_label, count in rows:
            label_key = momentum_label if momentum_label is not None else "未分類"
            tag_map[tag_id]["momentum_distribution"][label_key] += count
            tag_map[tag_id]["etf_count"] += count
            tag_info[tag_id] = {
                "id": tag_id,
                "name": name,
                "color": color,
                "category": cat,
            }

        # Build result list
        tags = []

        for tag_id, agg in tag_map.items():
            if agg["etf_count"] == 0:
                continue

            dist = dict(agg["momentum_distribution"])
            score = self._calc_momentum_score(dist)
            dominant = max(dist, key=dist.get)

            tags.append({
                **tag_info[tag_id],
                "etf_count": agg["etf_count"],
                "momentum_distribution": dist,
                "momentum_score": round(score, 1),
                "dominant_label": dominant,
            })

        # Get total unique ETF count
        etf_count_query = (
            db.session.query(func.count(func.distinct(ETFTagRelation.etf_code)))
            .join(Tag, Tag.id == ETFTagRelation.tag_id)
        )
        if category:
            etf_count_query = etf_count_query.filter(Tag.category == category)
        total_etf_count = etf_count_query.scalar() or 0

        # Get available categories
        categories = [
            row[0]
            for row in db.session.query(Tag.category)
            .filter(Tag.category.isnot(None))
            .distinct()
            .order_by(Tag.category)
            .all()
        ]

        return {
            "tags": sorted(tags, key=lambda t: t["momentum_score"], reverse=True),
            "categories": categories,
            "total_etf_count": total_etf_count,
        }

    def _calc_momentum_score(self, distribution: Dict[Optional[str], int]) -> float:
        """Calculate weighted average momentum score.

        Args:
            distribution: momentum_label -> count mapping

        Returns:
            Weighted average score (0-100)
        """
        total = 0
        weighted_sum = 0.0

        for label, count in distribution.items():
            score = MOMENTUM_SCORES.get(label, NEUTRAL_SCORE)
            weighted_sum += score * count
            total += count

        if total == 0:
            return NEUTRAL_SCORE

        return weighted_sum / total
