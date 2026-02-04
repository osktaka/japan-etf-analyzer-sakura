"""Tag service for tag business logic."""
from typing import List, Optional

from src.repositories import TagRepository


class TagService:
    """Service for tag operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = TagRepository()

    def get_all(self) -> List[dict]:
        """Get all tags with ETF count."""
        tags_with_count = self.repository.get_all_with_count()
        result = []
        for tag, etf_count in tags_with_count:
            tag_dict = tag.to_dict()
            tag_dict["etf_count"] = etf_count
            result.append(tag_dict)
        return result

    def get_by_id(self, tag_id: int) -> Optional[dict]:
        """Get tag by ID."""
        tag = self.repository.get_by_id(tag_id)
        if tag:
            return tag.to_dict()
        return None
