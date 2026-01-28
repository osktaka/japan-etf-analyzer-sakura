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
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    def __init__(self, user_repository: Optional[UserRepository] = None):
        """Initialize auth service."""
        self.user_repository = user_repository or UserRepository()

    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format."""
        if not email:
            return False, "メールアドレスは必須です"
        if not self.EMAIL_PATTERN.match(email):
            return False, "メールアドレスの形式が正しくありません"
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
        self, email: str, password: str, username: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user.

        Returns:
            Tuple of (user, error_message). User is None if error occurred.
        """
        # Validate input
        valid, error = self.validate_email(email)
        if not valid:
            return None, error

        valid, error = self.validate_password(password)
        if not valid:
            return None, error

        valid, error = self.validate_username(username)
        if not valid:
            return None, error

        # Check if email already exists
        if self.user_repository.email_exists(email):
            return None, "このメールアドレスは既に登録されています"

        # Create user
        user = User(email=email, username=username)
        user.set_password(password)

        try:
            self.user_repository.create(user)
            return user, None
        except Exception as e:
            self.user_repository.rollback()
            return None, f"ユーザー登録に失敗しました: {str(e)}"

    def login(
        self, email: str, password: str, remember: bool = False
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user and create session.

        Returns:
            Tuple of (user, error_message). User is None if authentication failed.
        """
        if not email or not password:
            return None, "メールアドレスとパスワードは必須です"

        user = self.user_repository.get_by_email(email)

        if user is None:
            return None, "メールアドレスまたはパスワードが正しくありません"

        if not user.is_active:
            return None, "このアカウントは無効化されています"

        if not user.check_password(password):
            return None, "メールアドレスまたはパスワードが正しくありません"

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
