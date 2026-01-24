"""Favorite repository for database operations."""
from typing import List, Optional

from src.models import Favorite, db

from .base_repository import BaseRepository


class FavoriteRepository(BaseRepository[Favorite]):
    """Repository for Favorite entity."""

    model = Favorite

    def get_by_user_id(self, user_id: int) -> List[Favorite]:
        """Get all favorites for a user."""
        return (
            db.session.query(Favorite)
            .filter(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
            .all()
        )

    def get_by_user_and_etf(self, user_id: int, etf_code: str) -> Optional[Favorite]:
        """Get favorite by user ID and ETF code."""
        return (
            db.session.query(Favorite)
            .filter(Favorite.user_id == user_id, Favorite.etf_code == etf_code)
            .first()
        )

    def exists(self, user_id: int, etf_code: str) -> bool:
        """Check if favorite exists."""
        return self.get_by_user_and_etf(user_id, etf_code) is not None

    def delete_by_user_and_etf(self, user_id: int, etf_code: str) -> bool:
        """Delete favorite by user ID and ETF code. Returns True if deleted."""
        favorite = self.get_by_user_and_etf(user_id, etf_code)
        if favorite:
            self.delete(favorite)
            return True
        return False

    def get_etf_codes_for_user(self, user_id: int) -> List[str]:
        """Get list of ETF codes that user has favorited."""
        favorites = self.get_by_user_id(user_id)
        return [f.etf_code for f in favorites]
