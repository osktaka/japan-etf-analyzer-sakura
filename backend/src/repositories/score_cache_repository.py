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
        self, perspective: str, limit: int = 10, scoring_mode: str = "full"
    ) -> List[ScoreCache]:
        """Get top scores for a perspective.

        Args:
            perspective: Scoring perspective
            limit: Maximum number of results
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            List of ScoreCache objects sorted by appropriate score descending
        """
        if scoring_mode == "full":
            return (
                ScoreCache.query.filter_by(perspective=perspective)
                .filter(ScoreCache.total_score_full.isnot(None))
                .order_by(ScoreCache.total_score_full.desc())
                .limit(limit)
                .all()
            )
        else:
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
        total_score_full: Optional[float] = None,
    ) -> ScoreCache:
        """Insert or update score cache.

        Args:
            etf_code: ETF code
            perspective: Scoring perspective
            total_score: Total composite score (partial mode)
            axis_scores: Dictionary of axis scores (dividend_power, cost_efficiency, etc.)
            total_score_full: Total composite score (full mode)

        Returns:
            ScoreCache object
        """
        existing = self.get_by_code_and_perspective(etf_code, perspective)

        if existing:
            existing.total_score = total_score
            existing.total_score_full = total_score_full
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
                total_score_full=total_score_full,
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

    def get_scores_with_axes(
        self, etf_codes: List[str], perspective: str, scoring_mode: str = "full"
    ) -> Dict[str, Dict]:
        """Get scores and axis scores for multiple ETFs.

        Args:
            etf_codes: List of ETF codes
            perspective: Perspective ID (balance, dividend, low-cost, etc.)
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Dict mapping ETF code to dict with score and axis_scores
            Example: {
                "1489": {
                    "score": 78.5,
                    "axis_scores": {"dividend_power": 80.0, ...}
                }
            }
        """
        cached_data = self.get_batch_scores(etf_codes, perspective)

        result = {}
        for code in etf_codes:
            cache = cached_data.get(code)
            if cache:
                # Select score based on mode
                score = (
                    cache.total_score_full
                    if scoring_mode == "full" and cache.total_score_full is not None
                    else cache.total_score
                )

                axis_scores = {
                    "dividend_power": cache.dividend_power,
                    "cost_efficiency": cache.cost_efficiency,
                    "scale_reliability": cache.scale_reliability,
                    "trading_quality": cache.trading_quality,
                    "return_performance": cache.return_performance,
                }

                result[code] = {
                    "score": score,
                    "axis_scores": axis_scores,
                }
            else:
                result[code] = {
                    "score": None,
                    "axis_scores": None,
                }

        return result
