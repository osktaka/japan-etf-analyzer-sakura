"""Tag service for tag business logic."""
from typing import List, Optional

from src.repositories import TagRepository


class TagService:
    """Service for tag operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = TagRepository()

    def get_all(self) -> List[dict]:
        """Get all tags sorted by name."""
        tags = self.repository.get_all_sorted()
        return [tag.to_dict() for tag in tags]

    def get_by_id(self, tag_id: int) -> Optional[dict]:
        """Get tag by ID."""
        tag = self.repository.get_by_id(tag_id)
        if tag:
            return tag.to_dict()
        return None
