"""ETF service for ETF business logic."""
from typing import Dict, List, Optional

from src.repositories import ETFRepository, ScoreCacheRepository
from src.services.scoring_service import ScoringService

# Map score sort fields to scoring service perspective keys
SCORE_SORT_FIELDS = {
    'score_balance': 'balance',
    'score_dividend': 'dividend',
    'score_low_cost': 'low-cost',
    'score_stability': 'stability',
    'score_volume': 'volume',
    'score_growth': 'growth',
}


class ETFService:
    """Service for ETF operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = ETFRepository()
        self.score_cache_repository = ScoreCacheRepository()
        self.scoring_service = ScoringService()

    def search(
        self,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        min_dividend_yield: Optional[float] = None,
        max_expense_ratio: Optional[float] = None,
        favorite_codes: Optional[List[str]] = None,
        holding_codes: Optional[List[str]] = None,
        sort: Optional[str] = None,
        order: str = "asc",
        return_type: str = "price",
        scoring_mode: str = "full",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """Search ETFs with filters."""
        # Check if this is a score sort
        is_score_sort = sort in SCORE_SORT_FIELDS

        if is_score_sort:
            # Score sort: get all matching ETFs, compute scores, sort, then paginate
            all_etfs = self.repository.search(
                keyword=keyword,
                category_id=category_id,
                tag_ids=tag_ids,
                min_dividend_yield=min_dividend_yield,
                max_expense_ratio=max_expense_ratio,
                favorite_codes=favorite_codes,
                holding_codes=holding_codes,
                sort=None,  # No DB sort
                order=order,
                return_type=return_type,
                limit=None,  # Get all
                offset=0,
            )

            # Get scores from cache (with fallback to calculation)
            codes = [etf.code for etf in all_etfs]
            all_scores = self.get_batch_scores(codes, scoring_mode)

            # Get the score key to sort by
            score_key = SCORE_SORT_FIELDS[sort]

            # Sort by score (missing scores = -1, sorted to end)
            all_etfs.sort(
                key=lambda etf: all_scores.get(etf.code, {}).get(score_key, -1),
                reverse=(order == 'desc')
            )

            # Apply pagination
            total = len(all_etfs)
            etfs = all_etfs[offset:offset + limit]
        else:
            # Normal sort: use repository pagination
            etfs = self.repository.search(
                keyword=keyword,
                category_id=category_id,
                tag_ids=tag_ids,
                min_dividend_yield=min_dividend_yield,
                max_expense_ratio=max_expense_ratio,
                favorite_codes=favorite_codes,
                holding_codes=holding_codes,
                sort=sort,
                order=order,
                return_type=return_type,
                limit=limit,
                offset=offset,
            )
            total = self.repository.count(
                keyword=keyword,
                category_id=category_id,
                tag_ids=tag_ids,
                min_dividend_yield=min_dividend_yield,
                max_expense_ratio=max_expense_ratio,
                favorite_codes=favorite_codes,
                holding_codes=holding_codes,
            )

        return {
            "items": [etf.to_summary_dict() for etf in etfs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_by_code(self, code: str) -> Optional[dict]:
        """Get ETF details by code."""
        etf = self.repository.get_by_code(code)
        if not etf:
            return None

        # Get basic ETF data
        result = etf.to_dict()

        # Get score from cache (balance perspective for detail view)
        score_caches = self.score_cache_repository.get_by_code(code)
        balance_cache = next(
            (cache for cache in score_caches if cache.perspective == 'balance'),
            None
        )

        if balance_cache:
            result['score'] = balance_cache.total_score
            result['score_full'] = balance_cache.total_score_full
            result['axis_scores'] = {
                'dividend_power': balance_cache.dividend_power,
                'cost_efficiency': balance_cache.cost_efficiency,
                'scale_reliability': balance_cache.scale_reliability,
                'trading_quality': balance_cache.trading_quality,
                'return_performance': balance_cache.return_performance,
            }
        else:
            result['score'] = None
            result['score_full'] = None
            result['axis_scores'] = None

        # Add score basis data
        # 30-day average volume
        result['average_volume'] = self.repository.get_average_volume(code, days=30)

        # Trading value (price × volume)
        if etf.market_price and result['average_volume']:
            result['trading_value'] = float(etf.market_price) * result['average_volume']
        else:
            result['trading_value'] = None

        # Return rates
        return_rates = self.repository.get_return_rates(code)
        result['return_1y'] = return_rates.get('1y')
        result['return_3y'] = return_rates.get('3y')

        return result

    def get_all(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get all ETFs with pagination."""
        etfs = self.repository.search(limit=limit, offset=offset)
        return {
            "items": [etf.to_summary_dict() for etf in etfs],
            "total": len(etfs),
            "limit": limit,
            "offset": offset,
        }

    def get_batch_scores(self, codes: List[str], scoring_mode: str = 'full') -> Dict[str, Dict[str, float]]:
        """Get all 6 perspective scores for multiple ETFs.

        Args:
            codes: List of ETF codes
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Dict mapping ETF code to dict of perspective scores
        """
        # Try to get from cache first
        cached_data = self.score_cache_repository.get_all_perspectives_batch(codes)

        result = {}
        missing_codes = []

        for code in codes:
            if code in cached_data and cached_data[code]:
                # Convert cached data to score dict based on scoring_mode
                if scoring_mode == 'partial':
                    result[code] = {
                        perspective: cache.total_score
                        for perspective, cache in cached_data[code].items()
                    }
                else:  # full mode (default)
                    result[code] = {
                        perspective: cache.total_score_full if cache.total_score_full is not None else cache.total_score
                        for perspective, cache in cached_data[code].items()
                    }
            else:
                missing_codes.append(code)

        # Fallback: calculate missing scores on-the-fly
        if missing_codes:
            calculated_scores = self.scoring_service.get_all_scores_batch(missing_codes)
            result.update(calculated_scores)

        return result
