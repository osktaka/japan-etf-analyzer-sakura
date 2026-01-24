"""Category service for category business logic."""
from typing import List, Optional

from src.models import Category
from src.repositories import CategoryRepository


class CategoryService:
    """Service for category operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = CategoryRepository()

    def get_all(self) -> List[dict]:
        """Get all categories sorted by sort_order."""
        categories = self.repository.get_all_sorted()
        return [cat.to_dict() for cat in categories]

    def get_by_id(self, category_id: int) -> Optional[dict]:
        """Get category by ID."""
        category = self.repository.get_by_id(category_id)
        if category:
            return category.to_dict()
        return None
