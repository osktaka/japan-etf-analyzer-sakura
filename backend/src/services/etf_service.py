"""ETF service for ETF business logic."""
from typing import Dict, List, Optional

from src.repositories import ETFRepository


class ETFService:
    """Service for ETF operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = ETFRepository()

    def search(
        self,
        keyword: Optional[str] = None,
        category_id: Optional[int] = None,
        tag_ids: Optional[List[int]] = None,
        min_dividend_yield: Optional[float] = None,
        max_expense_ratio: Optional[float] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict:
        """Search ETFs with filters."""
        etfs = self.repository.search(
            keyword=keyword,
            category_id=category_id,
            tag_ids=tag_ids,
            min_dividend_yield=min_dividend_yield,
            max_expense_ratio=max_expense_ratio,
            limit=limit,
            offset=offset,
        )

        return {
            "items": [etf.to_summary_dict() for etf in etfs],
            "total": len(etfs),
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
