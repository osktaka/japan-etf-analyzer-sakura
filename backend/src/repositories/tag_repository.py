"""Tag repository for tag data access."""
from typing import List, Optional

from src.models import Tag, db

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

    def create_if_not_exists(self, name: str, color: str = "#6B7280") -> Tag:
        """Create tag if it doesn't exist, otherwise return existing."""
        existing = self.get_by_name(name)
        if existing:
            return existing

        tag = Tag(name=name, color=color)
        return self.create(tag)
