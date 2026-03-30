"""Stock split repository for database operations."""
from datetime import date, datetime
from typing import List, Optional

from src.models import StockSplit, db

from .base_repository import BaseRepository


class StockSplitRepository(BaseRepository[StockSplit]):
    """Repository for StockSplit entity."""

    model = StockSplit

    def get_by_etf_code_and_date(
        self, etf_code: str, split_date: date
    ) -> Optional[StockSplit]:
        """Find stock split by ETF code and split date."""
        return (
            db.session.query(StockSplit)
            .filter(
                StockSplit.etf_code == etf_code, StockSplit.split_date == split_date
            )
            .first()
        )

    def get_by_etf_code(self, etf_code: str) -> List[StockSplit]:
        """Get all stock splits for a specific ETF code."""
        return (
            db.session.query(StockSplit)
            .filter(StockSplit.etf_code == etf_code)
            .order_by(StockSplit.split_date.desc())
            .all()
        )

    def get_approved_splits_since(
        self, etf_code: str, since_date: date
    ) -> List[StockSplit]:
        """Get applied stock splits for an ETF since a specific date."""
        return (
            db.session.query(StockSplit)
            .filter(
                StockSplit.etf_code == etf_code,
                StockSplit.is_applied.is_(True),
                StockSplit.split_date > since_date,
            )
            .order_by(StockSplit.split_date.asc())
            .all()
        )

    def get_chart_applied_splits_since(
        self, etf_code: str, since_date: date
    ) -> List[StockSplit]:
        """Get chart-applied stock splits for an ETF since a specific date."""
        return (
            db.session.query(StockSplit)
            .filter(
                StockSplit.etf_code == etf_code,
                StockSplit.is_chart_applied.is_(True),
                StockSplit.split_date >= since_date,
            )
            .order_by(StockSplit.split_date.asc())
            .all()
        )

    def get_approved_splits_between(
        self, etf_code: str, start_date: date, end_date: date
    ) -> List[StockSplit]:
        """Get applied stock splits for an ETF between two dates (exclusive of start, inclusive of end)."""
        return (
            db.session.query(StockSplit)
            .filter(
                StockSplit.etf_code == etf_code,
                StockSplit.is_applied.is_(True),
                StockSplit.split_date > start_date,
                StockSplit.split_date <= end_date,
            )
            .order_by(StockSplit.split_date.asc())
            .all()
        )

    def update_applied(
        self, split_id: int, is_applied: bool, reviewed_by: int
    ) -> Optional[StockSplit]:
        """Update the applied status of a stock split."""
        split = self.get_by_id(split_id)
        if split:
            split.is_applied = is_applied
            split.reviewed_at = datetime.utcnow()
            split.reviewed_by = reviewed_by
            db.session.commit()
        return split

    def exists(self, etf_code: str, split_date: date) -> bool:
        """Check if a stock split already exists for the given ETF code and date."""
        return (
            db.session.query(StockSplit)
            .filter(
                StockSplit.etf_code == etf_code, StockSplit.split_date == split_date
            )
            .first()
            is not None
        )
