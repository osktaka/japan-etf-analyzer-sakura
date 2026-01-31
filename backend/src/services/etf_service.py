"""ETF service for ETF business logic."""
from typing import Dict, List, Optional

from src.repositories import ETFRepository
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

            # Compute scores for all ETFs
            codes = [etf.code for etf in all_etfs]
            all_scores = self.scoring_service.get_all_scores_batch(codes)

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
        if etf:
            return etf.to_dict()
        return None

    def get_all(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get all ETFs with pagination."""
        etfs = self.repository.search(limit=limit, offset=offset)
        return {
            "items": [etf.to_summary_dict() for etf in etfs],
            "total": len(etfs),
            "limit": limit,
            "offset": offset,
        }

    def get_batch_scores(self, codes: List[str]) -> Dict[str, Dict[str, float]]:
        """Get all 6 perspective scores for multiple ETFs.

        Args:
            codes: List of ETF codes

        Returns:
            Dict mapping ETF code to dict of perspective scores
        """
        return self.scoring_service.get_all_scores_batch(codes)
