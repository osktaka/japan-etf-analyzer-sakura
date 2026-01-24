"""User repository for database operations."""
from typing import List, Optional

from src.models import User, db

from .base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entity."""

    model = User

    def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email address."""
        return db.session.query(User).filter(User.email == email).first()

    def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        return db.session.query(User).filter(User.email == email).first() is not None

    def get_active_users(self) -> List[User]:
        """Get all active users."""
        return db.session.query(User).filter(User.is_active.is_(True)).all()
