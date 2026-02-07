"""Authentication service."""
import re
from datetime import datetime
from typing import Optional, Tuple

from flask_login import login_user, logout_user

from src.models import User
from src.repositories.user_repository import UserRepository


class AuthService:
    """Service for authentication operations."""

    MIN_PASSWORD_LENGTH = 8
    MAX_USERNAME_LENGTH = 50
    USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")

    def __init__(self, user_repository: Optional[UserRepository] = None):
        """Initialize auth service."""
        self.user_repository = user_repository or UserRepository()

    def validate_user_id(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Validate user_id format."""
        if not user_id:
            return False, "ユーザーIDは必須です"
        if not self.USER_ID_PATTERN.match(user_id):
            return (
                False,
                "ユーザーIDは3〜50文字の英数字、ハイフン、アンダースコアのみ使用可能です",
            )
        return True, None

    def validate_password(self, password: str) -> Tuple[bool, Optional[str]]:
        """Validate password requirements."""
        if not password:
            return False, "パスワードは必須です"
        if len(password) < self.MIN_PASSWORD_LENGTH:
            return False, f"パスワードは{self.MIN_PASSWORD_LENGTH}文字以上必要です"
        return True, None

    def validate_username(self, username: str) -> Tuple[bool, Optional[str]]:
        """Validate username requirements."""
        if not username:
            return False, "ユーザー名は必須です"
        if len(username) > self.MAX_USERNAME_LENGTH:
            return False, f"ユーザー名は{self.MAX_USERNAME_LENGTH}文字以内です"
        return True, None

    def register(
        self, user_id: str, password: str, username: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user.

        Returns:
            Tuple of (user, error_message). User is None if error occurred.
        """
        # Validate input
        valid, error = self.validate_user_id(user_id)
        if not valid:
            return None, error

        valid, error = self.validate_password(password)
        if not valid:
            return None, error

        valid, error = self.validate_username(username)
        if not valid:
            return None, error

        # Check if user_id already exists
        if self.user_repository.user_id_exists(user_id):
            return None, "このユーザーIDは既に登録されています"

        # Create user
        user = User(user_id=user_id, username=username)
        user.set_password(password)

        try:
            self.user_repository.create(user)
            # Auto-login after registration
            login_user(user)
            return user, None
        except Exception as e:
            self.user_repository.rollback()
            return None, f"ユーザー登録に失敗しました: {str(e)}"

    def login(
        self, user_id: str, password: str, remember: bool = False
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user and create session.

        Returns:
            Tuple of (user, error_message). User is None if authentication failed.
        """
        if not user_id or not password:
            return None, "ユーザーIDとパスワードは必須です"

        user = self.user_repository.get_by_user_id(user_id)

        if user is None:
            return None, "ユーザーIDまたはパスワードが正しくありません"

        if not user.is_active:
            return None, "このアカウントは無効化されています"

        if not user.check_password(password):
            return None, "ユーザーIDまたはパスワードが正しくありません"

        # Update last login time
        user.last_login_at = datetime.utcnow()
        self.user_repository.update(user)

        # Create session
        login_user(user, remember=remember)
        return user, None

    def logout(self) -> None:
        """Logout current user."""
        logout_user()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID for Flask-Login."""
        return self.user_repository.get_by_id(user_id)

    def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password.

        Returns:
            Tuple of (success, error_message). success is False if error occurred.
        """
        # Verify current password
        if not user.check_password(current_password):
            return False, "現在のパスワードが正しくありません"

        # Validate new password
        valid, error = self.validate_password(new_password)
        if not valid:
            return False, error

        # Update password
        try:
            user.set_password(new_password)
            self.user_repository.update(user)
            return True, None
        except Exception as e:
            self.user_repository.rollback()
            return False, f"パスワード変更に失敗しました: {str(e)}"
