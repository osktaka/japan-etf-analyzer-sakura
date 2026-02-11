"""CashFlow repository for database operations."""
from datetime import date
from typing import List, Optional

from src.models import CashFlow, db

from .base_repository import BaseRepository


class CashFlowRepository(BaseRepository[CashFlow]):
    """Repository for CashFlow entity."""

    model = CashFlow

    def get_by_user_id(self, user_id: int) -> List[CashFlow]:
        """Get all cash flows for a user ordered by flow date desc."""
        return (
            db.session.query(CashFlow)
            .filter(CashFlow.user_id == user_id)
            .order_by(CashFlow.flow_date.desc(), CashFlow.created_at.desc())
            .all()
        )

    def get_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[CashFlow]:
        """Get cash flows within a date range."""
        query = db.session.query(CashFlow).filter(CashFlow.user_id == user_id)
        if start_date:
            query = query.filter(CashFlow.flow_date >= start_date)
        if end_date:
            query = query.filter(CashFlow.flow_date <= end_date)
        return query.order_by(CashFlow.flow_date.desc(), CashFlow.created_at.desc()).all()
