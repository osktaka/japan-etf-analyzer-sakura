"""Category repository for category data access."""
from typing import List, Optional

from src.models import Category, db

from .base_repository import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category operations."""

    model = Category

    def get_by_name(self, name: str) -> Optional[Category]:
        """Get category by name."""
        return db.session.query(Category).filter_by(name=name).first()

    def get_all_sorted(self) -> List[Category]:
        """Get all categories sorted by sort_order."""
        return (
            db.session.query(Category).order_by(Category.sort_order, Category.id).all()
        )

    def create_if_not_exists(
        self, name: str, description: str = None, sort_order: int = 0
    ) -> Category:
        """Create category if it doesn't exist, otherwise return existing."""
        existing = self.get_by_name(name)
        if existing:
            return existing

        category = Category(name=name, description=description, sort_order=sort_order)
        return self.create(category)
