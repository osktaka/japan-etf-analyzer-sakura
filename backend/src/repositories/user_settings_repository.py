"""UserSettings repository for database operations."""
from typing import Optional

from src.models import UserSettings, db

from .base_repository import BaseRepository


class UserSettingsRepository(BaseRepository[UserSettings]):
    """Repository for UserSettings entity."""

    model = UserSettings

    def get_by_user_id(self, user_id: int) -> Optional[UserSettings]:
        """Find user settings by user_id."""
        return (
            db.session.query(UserSettings)
            .filter(UserSettings.user_id == user_id)
            .first()
        )

    def create_or_update(
        self, user_id: int, custom_weights: str
    ) -> UserSettings:
        """Create or update user settings."""
        settings = self.get_by_user_id(user_id)
        if settings:
            settings.custom_weights = custom_weights
        else:
            settings = UserSettings(user_id=user_id, custom_weights=custom_weights)
            db.session.add(settings)
        db.session.commit()
        return settings
