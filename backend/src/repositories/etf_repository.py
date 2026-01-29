"""ETF repository for ETF data access."""
from typing import List, Optional

from sqlalchemy import or_

from src.models import ETF, ETFTagRelation, Category, Tag, PerformanceCache, db

from .base_repository import BaseRepository


SORT_COLUMNS = {
    "code": ETF.code,
    "name": ETF.name,
    "price": ETF.market_price,
    "dividend_yield": ETF.dividend_yield,
    "expense_ratio": ETF.expense_ratio,
    "total_assets": ETF.total_assets,
}

# Performance sort options (maps to period in performance_cache)
PERFORMANCE_SORT_PERIODS = {
    "return_1m": "1m",
    "return_3m": "3m",
    "return_6m": "6m",
    "return_1y": "1y",
    "return_3y": "3y",
    "return_5y": "5y",
    "return_10y": "10y",
    "return_20y": "20y",
}


class ETFRepository(BaseRepository[ETF]):
    """Repository for ETF operations."""

    model = ETF

    def get_by_code(self, code: str) -> Optional[ETF]:
        """Get ETF by code."""
        return db.session.get(ETF, code)

    def _build_filter_query(
        self,
        keyword: str = None,
        category_id: int = None,
        tag_ids: List[int] = None,
        min_dividend_yield: float = None,
        max_expense_ratio: float = None,
        favorite_codes: List[str] = None,
        holding_codes: List[str] = None,
    ):
        """Build filtered query with common conditions."""
        query = db.session.query(ETF)

        if keyword:
            search_term = f"%{keyword}%"
            query = (
                query.outerjoin(ETF.category)
                .outerjoin(ETF.tag_relations)
                .outerjoin(ETFTagRelation.tag)
                .filter(
                    or_(
                        ETF.code.ilike(search_term),
                        ETF.name.ilike(search_term),
                        ETF.description.ilike(search_term),
                        Category.name.ilike(search_term),
                        Tag.name.ilike(search_term),
                    )
                )
                .distinct()
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

        if favorite_codes:
            query = query.filter(ETF.code.in_(favorite_codes))

        if holding_codes:
            query = query.filter(ETF.code.in_(holding_codes))

        return query

    def search(
        self,
        keyword: str = None,
        category_id: int = None,
        tag_ids: List[int] = None,
        min_dividend_yield: float = None,
        max_expense_ratio: float = None,
        favorite_codes: List[str] = None,
        holding_codes: List[str] = None,
        sort: str = None,
        order: str = "asc",
        return_type: str = "price",
        limit: int = 50,
        offset: int = 0,
    ) -> List[ETF]:
        """Search ETFs with filters."""
        query = self._build_filter_query(
            keyword=keyword,
            category_id=category_id,
            tag_ids=tag_ids,
            min_dividend_yield=min_dividend_yield,
            max_expense_ratio=max_expense_ratio,
            favorite_codes=favorite_codes,
            holding_codes=holding_codes,
        )

        if sort and sort in SORT_COLUMNS:
            column = SORT_COLUMNS[sort]
            if order == "desc":
                query = query.order_by(column.desc().nulls_last())
            else:
                query = query.order_by(column.asc().nulls_last())
        elif sort and sort in PERFORMANCE_SORT_PERIODS:
            # Join with performance_cache for sorting by return rate or regression rate
            period = PERFORMANCE_SORT_PERIODS[sort]
            query = query.outerjoin(
                PerformanceCache,
                (ETF.code == PerformanceCache.etf_code)
                & (PerformanceCache.period == period),
            )
            # Choose sort column based on return_type
            sort_column = (
                PerformanceCache.regression_rate
                if return_type == "regression"
                else PerformanceCache.return_rate
            )
            if order == "desc":
                query = query.order_by(sort_column.desc().nulls_last())
            else:
                query = query.order_by(sort_column.asc().nulls_last())
        else:
            query = query.order_by(ETF.code.asc())

        return query.offset(offset).limit(limit).all()

    def count(
        self,
        keyword: str = None,
        category_id: int = None,
        tag_ids: List[int] = None,
        min_dividend_yield: float = None,
        max_expense_ratio: float = None,
        favorite_codes: List[str] = None,
        holding_codes: List[str] = None,
    ) -> int:
        """Count ETFs matching filters."""
        query = self._build_filter_query(
            keyword=keyword,
            category_id=category_id,
            tag_ids=tag_ids,
            min_dividend_yield=min_dividend_yield,
            max_expense_ratio=max_expense_ratio,
            favorite_codes=favorite_codes,
            holding_codes=holding_codes,
        )
        return query.count()

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
