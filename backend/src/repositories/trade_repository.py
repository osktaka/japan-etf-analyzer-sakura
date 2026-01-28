"""Trade repository for database operations."""
from datetime import date
from typing import List, Optional

from src.models import ETF, Trade, db

from .base_repository import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade entity."""

    model = Trade

    def get_by_user_id(self, user_id: int) -> List[Trade]:
        """Get all trades for a user ordered by trade date desc."""
        return (
            db.session.query(Trade)
            .filter(Trade.user_id == user_id)
            .order_by(Trade.trade_date.desc(), Trade.created_at.desc())
            .all()
        )

    def get_by_user_and_etf(self, user_id: int, etf_code: str) -> List[Trade]:
        """Get all trades for a user and specific ETF."""
        return (
            db.session.query(Trade)
            .filter(Trade.user_id == user_id, Trade.etf_code == etf_code)
            .order_by(Trade.trade_date.desc())
            .all()
        )

    def get_by_date_range(
        self, user_id: int, start_date: date, end_date: date
    ) -> List[Trade]:
        """Get trades within a date range."""
        return (
            db.session.query(Trade)
            .filter(
                Trade.user_id == user_id,
                Trade.trade_date >= start_date,
                Trade.trade_date <= end_date,
            )
            .order_by(Trade.trade_date.desc())
            .all()
        )

    def get_user_etf_codes(self, user_id: int) -> List[str]:
        """Get unique ETF codes that user has traded."""
        result = (
            db.session.query(Trade.etf_code)
            .filter(Trade.user_id == user_id)
            .distinct()
            .all()
        )
        return [r[0] for r in result]

    def get_filtered(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
    ) -> List[Trade]:
        """Get trades with optional filters.

        Args:
            user_id: User ID
            start_date: Filter trades on or after this date
            end_date: Filter trades on or before this date
            search: Search ETF code or name (partial match)

        Returns:
            List of Trade objects
        """
        query = db.session.query(Trade).filter(Trade.user_id == user_id)

        if start_date is not None:
            query = query.filter(Trade.trade_date >= start_date)

        if end_date is not None:
            query = query.filter(Trade.trade_date <= end_date)

        if search:
            # JOINしてETFのcodeまたはnameで部分一致検索
            query = query.join(ETF, Trade.etf_code == ETF.code).filter(
                db.or_(
                    ETF.code.ilike(f"%{search}%"),
                    ETF.name.ilike(f"%{search}%"),
                )
            )

        return query.order_by(Trade.trade_date.desc(), Trade.created_at.desc()).all()
