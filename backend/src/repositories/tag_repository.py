"""Tag repository for tag data access."""
from typing import List, Optional, Tuple

from sqlalchemy import func

from src.models import ETFTagRelation, Tag, db

from .base_repository import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository for Tag operations."""

    model = Tag

    def get_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name."""
        return db.session.query(Tag).filter_by(name=name).first()

    def get_by_names(self, names: List[str]) -> List[Tag]:
        """Get tags by list of names."""
        return db.session.query(Tag).filter(Tag.name.in_(names)).all()

    def get_all_sorted(self) -> List[Tag]:
        """Get all tags sorted by name."""
        return db.session.query(Tag).order_by(Tag.name).all()

    def get_all_with_count(self) -> List[Tuple[Tag, int]]:
        """Get all tags with ETF count using LEFT JOIN.

        Returns:
            List of tuples: (Tag, etf_count)
        """
        result = (
            db.session.query(Tag, func.count(ETFTagRelation.etf_code).label("etf_count"))
            .outerjoin(ETFTagRelation, Tag.id == ETFTagRelation.tag_id)
            .group_by(Tag.id)
            .order_by(Tag.name)
            .all()
        )
        return result

    def create_if_not_exists(
        self, name: str, color: str = "#6B7280", category: str = None
    ) -> Tag:
        """Create tag if it doesn't exist, otherwise return existing."""
        existing = self.get_by_name(name)
        if existing:
            return existing

        tag = Tag(name=name, color=color, category=category)
        return self.create(tag)
