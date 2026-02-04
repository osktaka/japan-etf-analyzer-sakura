"""User repository for database operations."""
from typing import List, Optional

from src.models import User, db

from .base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity."""

    model = User

    def get_by_user_id(self, user_id: str) -> Optional[User]:
        """Find user by user_id."""
        return db.session.query(User).filter(User.user_id == user_id).first()

    def user_id_exists(self, user_id: str) -> bool:
        """Check if user_id already exists."""
        return db.session.query(User).filter(User.user_id == user_id).first() is not None

    def get_active_users(self) -> List[User]:
        """Get all active users."""
        return db.session.query(User).filter(User.is_active.is_(True)).all()
