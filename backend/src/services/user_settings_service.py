"""UserSettings service for business logic."""
import json
from typing import Dict, Optional, Tuple

from src.models import UserSettings
from src.repositories.user_settings_repository import UserSettingsRepository


class UserSettingsService:
    """Service for user settings operations."""

    def __init__(self):
        """Initialize service with repository."""
        self.repository = UserSettingsRepository()

    def get_custom_weights(self, user_id: int) -> Optional[Dict[str, float]]:
        """
        Get custom weights for a user in 0-1 format.

        Args:
            user_id: User ID

        Returns:
            Dictionary of weights in 0-1 format (e.g., {"流動性": 0.3}),
            or None if no custom weights exist
        """
        settings = self.repository.get_by_user_id(user_id)
        if not settings:
            return None

        try:
            weights_percent = json.loads(settings.custom_weights)
            # Convert from 0-100 to 0-1
            return {key: value / 100.0 for key, value in weights_percent.items()}
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def save_custom_weights(
        self, user_id: int, weights: Dict[str, int]
    ) -> UserSettings:
        """
        Save custom weights for a user.

        Args:
            user_id: User ID
            weights: Dictionary of weights in 0-100 format (e.g., {"流動性": 30})

        Returns:
            Created or updated UserSettings

        Raises:
            ValueError: If weights validation fails
        """
        is_valid, error_msg = self.validate_weights(weights)
        if not is_valid:
            raise ValueError(error_msg)

        custom_weights_json = json.dumps(weights, ensure_ascii=False)
        return self.repository.create_or_update(user_id, custom_weights_json)

    def validate_weights(self, weights: Dict[str, int]) -> Tuple[bool, Optional[str]]:
        """
        Validate custom weights.

        Args:
            weights: Dictionary of weights in 0-100 format

        Returns:
            Tuple of (is_valid, error_message)
            error_message is None if valid
        """
        required_keys = {
            "dividend_power",
            "cost_efficiency",
            "scale_reliability",
            "trading_quality",
            "return_performance",
        }

        # Check for missing keys
        missing_keys = required_keys - set(weights.keys())
        if missing_keys:
            return False, f"不足しているキー: {', '.join(missing_keys)}"

        # Check for extra keys
        extra_keys = set(weights.keys()) - required_keys
        if extra_keys:
            return False, f"不正なキー: {', '.join(extra_keys)}"

        # Check each value is 0-100
        for key, value in weights.items():
            if not isinstance(value, (int, float)):
                return False, f"{key}の値が数値ではありません"
            if not 0 <= value <= 100:
                return False, f"{key}の値が0-100の範囲外です: {value}"

        # Check sum equals 100
        total = sum(weights.values())
        if abs(total - 100) > 0.01:  # Allow floating point tolerance
            return False, f"合計が100%ではありません: {total}"

        return True, None
