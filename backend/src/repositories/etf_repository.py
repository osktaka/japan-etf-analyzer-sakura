"""ETF repository for ETF data access."""
from typing import List, Optional

from sqlalchemy import or_

from src.models import Category, ETF, ETFTagRelation, Tag, db

from .base_repository import BaseRepository


class ETFRepository(BaseRepository[ETF]):
    """Repository for ETF operations."""

    model = ETF

    def get_by_code(self, code: str) -> Optional[ETF]:
        """Get ETF by code."""
        return db.session.get(ETF, code)

    def search(
        self,
        keyword: str = None,
        category_id: int = None,
        tag_ids: List[int] = None,
        min_dividend_yield: float = None,
        max_expense_ratio: float = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ETF]:
        """Search ETFs with filters."""
        query = db.session.query(ETF)

        if keyword:
            search_term = f"%{keyword}%"
            query = query.filter(
                or_(
                    ETF.code.ilike(search_term),
                    ETF.name.ilike(search_term),
                    ETF.description.ilike(search_term),
                )
            )

        if category_id:
            query = query.filter(ETF.category_id == category_id)

        if tag_ids:
            query = query.join(ETFTagRelation).filter(
                ETFTagRelation.tag_id.in_(tag_ids)
            )

        if min_dividend_yield is not None:
            query = query.filter(ETF.dividend_yield >= min_dividend_yield)

        if max_expense_ratio is not None:
            query = query.filter(ETF.expense_ratio <= max_expense_ratio)

        return query.offset(offset).limit(limit).all()

    def get_by_category(self, category_id: int) -> List[ETF]:
        """Get ETFs by category."""
        return db.session.query(ETF).filter_by(category_id=category_id).all()

    def get_by_tag(self, tag_id: int) -> List[ETF]:
        """Get ETFs by tag."""
        return (
            db.session.query(ETF)
            .join(ETFTagRelation)
            .filter(ETFTagRelation.tag_id == tag_id)
            .all()
        )

    def get_high_dividend(self, limit: int = 10) -> List[ETF]:
        """Get ETFs with highest dividend yield."""
        return (
            db.session.query(ETF)
            .filter(ETF.dividend_yield.isnot(None))
            .order_by(ETF.dividend_yield.desc())
            .limit(limit)
            .all()
        )

    def get_low_cost(self, limit: int = 10) -> List[ETF]:
        """Get ETFs with lowest expense ratio."""
        return (
            db.session.query(ETF)
            .filter(ETF.expense_ratio.isnot(None))
            .order_by(ETF.expense_ratio.asc())
            .limit(limit)
            .all()
        )

    def add_tag(self, etf_code: str, tag_id: int) -> Optional[ETFTagRelation]:
        """Add tag to ETF."""
        existing = (
            db.session.query(ETFTagRelation)
            .filter_by(etf_code=etf_code, tag_id=tag_id)
            .first()
        )
        if existing:
            return existing

        relation = ETFTagRelation(etf_code=etf_code, tag_id=tag_id)
        db.session.add(relation)
        db.session.commit()
        return relation

    def remove_tag(self, etf_code: str, tag_id: int) -> bool:
        """Remove tag from ETF."""
        relation = (
            db.session.query(ETFTagRelation)
            .filter_by(etf_code=etf_code, tag_id=tag_id)
            .first()
        )
        if not relation:
            return False

        db.session.delete(relation)
        db.session.commit()
        return True

    def create_or_update(self, etf_data: dict) -> ETF:
        """Create or update ETF from dictionary."""
        code = etf_data.get("code")
        etf = self.get_by_code(code)

        if etf:
            for key, value in etf_data.items():
                if key != "code" and hasattr(etf, key):
                    setattr(etf, key, value)
        else:
            etf = ETF(**etf_data)
            db.session.add(etf)

        db.session.commit()
        return etf
