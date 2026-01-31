"""Repository for ScoreCache model."""
from datetime import datetime
from typing import Dict, List, Optional

from src.models import ScoreCache, db

from .base_repository import BaseRepository


class ScoreCacheRepository(BaseRepository):
    """Repository for managing score cache data."""

    model = ScoreCache

    def __init__(self):
        """Initialize repository with ScoreCache model."""
        super().__init__()

    def get_by_code_and_perspective(
        self, etf_code: str, perspective: str
    ) -> Optional[ScoreCache]:
        """Get score cache by ETF code and perspective.

        Args:
            etf_code: ETF code
            perspective: Scoring perspective

        Returns:
            ScoreCache object or None
        """
        return ScoreCache.query.filter_by(
            etf_code=etf_code, perspective=perspective
        ).first()

    def get_by_code(self, etf_code: str) -> List[ScoreCache]:
        """Get all score caches for an ETF.

        Args:
            etf_code: ETF code

        Returns:
            List of ScoreCache objects
        """
        return ScoreCache.query.filter_by(etf_code=etf_code).all()

    def get_scores_for_perspective(
        self, perspective: str, limit: int = 10
    ) -> List[ScoreCache]:
        """Get top scores for a perspective.

        Args:
            perspective: Scoring perspective
            limit: Maximum number of results

        Returns:
            List of ScoreCache objects sorted by total_score descending
        """
        return (
            ScoreCache.query.filter_by(perspective=perspective)
            .filter(ScoreCache.total_score.isnot(None))
            .order_by(ScoreCache.total_score.desc())
            .limit(limit)
            .all()
        )

    def upsert(
        self,
        etf_code: str,
        perspective: str,
        total_score: float,
        axis_scores: Dict[str, Optional[float]],
    ) -> ScoreCache:
        """Insert or update score cache.

        Args:
            etf_code: ETF code
            perspective: Scoring perspective
            total_score: Total composite score
            axis_scores: Dictionary of axis scores (dividend_power, cost_efficiency, etc.)

        Returns:
            ScoreCache object
        """
        existing = self.get_by_code_and_perspective(etf_code, perspective)

        if existing:
            existing.total_score = total_score
            existing.dividend_power = axis_scores.get("dividend_power")
            existing.cost_efficiency = axis_scores.get("cost_efficiency")
            existing.scale_reliability = axis_scores.get("scale_reliability")
            existing.trading_quality = axis_scores.get("trading_quality")
            existing.return_performance = axis_scores.get("return_performance")
            existing.calculated_at = datetime.utcnow()
        else:
            cache = ScoreCache(
                etf_code=etf_code,
                perspective=perspective,
                total_score=total_score,
                dividend_power=axis_scores.get("dividend_power"),
                cost_efficiency=axis_scores.get("cost_efficiency"),
                scale_reliability=axis_scores.get("scale_reliability"),
                trading_quality=axis_scores.get("trading_quality"),
                return_performance=axis_scores.get("return_performance"),
                calculated_at=datetime.utcnow(),
            )
            db.session.add(cache)
            existing = cache

        db.session.commit()
        return existing

    def delete_by_code(self, etf_code: str) -> int:
        """Delete all score caches for an ETF.

        Args:
            etf_code: ETF code

        Returns:
            Number of deleted records
        """
        count = ScoreCache.query.filter_by(etf_code=etf_code).delete()
        db.session.commit()
        return count

    def get_batch_scores(
        self, etf_codes: List[str], perspective: str
    ) -> Dict[str, ScoreCache]:
        """Get score caches for multiple ETFs and a perspective.

        Args:
            etf_codes: List of ETF codes
            perspective: Scoring perspective

        Returns:
            Dictionary mapping ETF code to ScoreCache object
        """
        caches = (
            ScoreCache.query.filter(ScoreCache.etf_code.in_(etf_codes))
            .filter_by(perspective=perspective)
            .all()
        )
        return {cache.etf_code: cache for cache in caches}

    def get_all_perspectives_batch(
        self, etf_codes: List[str]
    ) -> Dict[str, Dict[str, ScoreCache]]:
        """Get all perspectives for multiple ETFs.

        Args:
            etf_codes: List of ETF codes

        Returns:
            Dictionary mapping ETF code to dict of perspective -> ScoreCache
            Example: {"1489": {"balance": ScoreCache(...), "dividend": ScoreCache(...), ...}}
        """
        caches = ScoreCache.query.filter(ScoreCache.etf_code.in_(etf_codes)).all()

        result: Dict[str, Dict[str, ScoreCache]] = {}
        for cache in caches:
            if cache.etf_code not in result:
                result[cache.etf_code] = {}
            result[cache.etf_code][cache.perspective] = cache

        return result
