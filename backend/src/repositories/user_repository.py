"""User repository for database operations."""
import secrets
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
        return (
            db.session.query(User).filter(User.user_id == user_id).first() is not None
        )

    def get_active_users(self) -> List[User]:
        """Get all active users."""
        return db.session.query(User).filter(User.is_active.is_(True)).all()

    def get_all_ordered_by_created_desc(self) -> List[User]:
        """Get all users, newest first."""
        return db.session.query(User).order_by(User.created_at.desc()).all()

    def update_admin_status(self, user_id: int, is_admin: bool) -> Optional[User]:
        """Update the admin flag of a user.

        Args:
            user_id: Target user's primary key
            is_admin: New admin flag value

        Returns:
            Updated User instance, or None if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.is_admin = is_admin
        db.session.commit()
        return user

    def reset_password(self, user_id: int) -> Optional[str]:
        """Reset a user's password to a freshly generated temporary one.

        Args:
            user_id: Target user's primary key

        Returns:
            The generated temporary password (plaintext, to hand to the admin
            for delivery), or None if the user was not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return None

        temporary_password = secrets.token_urlsafe(12)
        user.set_password(temporary_password)
        db.session.commit()
        return temporary_password
