"""Tests for AuthService."""
import pytest

from src.services.auth_service import AuthService


class TestAuthServiceValidation:
    """Test cases for AuthService validation."""

    @pytest.fixture
    def auth_service(self, db_session):
        """Create AuthService instance."""
        return AuthService()

    def test_validate_email_valid(self, auth_service):
        """Test valid email validation."""
        valid, error = auth_service.validate_email("test@example.com")
        assert valid is True
        assert error is None

    def test_validate_email_empty(self, auth_service):
        """Test empty email validation."""
        valid, error = auth_service.validate_email("")
        assert valid is False
        assert error == "メールアドレスは必須です"

    def test_validate_email_invalid_format(self, auth_service):
        """Test invalid email format."""
        valid, error = auth_service.validate_email("invalid-email")
        assert valid is False
        assert error == "メールアドレスの形式が正しくありません"

    def test_validate_password_valid(self, auth_service):
        """Test valid password."""
        valid, error = auth_service.validate_password("password123")
        assert valid is True
        assert error is None

    def test_validate_password_empty(self, auth_service):
        """Test empty password."""
        valid, error = auth_service.validate_password("")
        assert valid is False
        assert error == "パスワードは必須です"

    def test_validate_password_too_short(self, auth_service):
        """Test password too short."""
        valid, error = auth_service.validate_password("short")
        assert valid is False
        assert "8文字以上" in error

    def test_validate_username_valid(self, auth_service):
        """Test valid username."""
        valid, error = auth_service.validate_username("Test User")
        assert valid is True
        assert error is None

    def test_validate_username_empty(self, auth_service):
        """Test empty username."""
        valid, error = auth_service.validate_username("")
        assert valid is False
        assert error == "ユーザー名は必須です"

    def test_validate_username_too_long(self, auth_service):
        """Test username too long."""
        long_name = "a" * 51
        valid, error = auth_service.validate_username(long_name)
        assert valid is False
        assert "50文字以内" in error


class TestAuthServiceRegister:
    """Test cases for AuthService register."""

    @pytest.fixture
    def auth_service(self, db_session):
        """Create AuthService instance."""
        return AuthService()

    def test_register_success(self, auth_service, db_session):
        """Test successful user registration."""
        user, error = auth_service.register(
            email="newuser@example.com",
            password="password123",
            username="New User",
        )

        assert error is None
        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.username == "New User"
        assert user.id is not None

    def test_register_duplicate_email(self, auth_service, db_session):
        """Test registration with duplicate email."""
        # First registration
        auth_service.register(
            email="test@example.com",
            password="password123",
            username="User 1",
        )

        # Second registration with same email
        user, error = auth_service.register(
            email="test@example.com",
            password="password456",
            username="User 2",
        )

        assert user is None
        assert error == "このメールアドレスは既に登録されています"

    def test_register_invalid_email(self, auth_service, db_session):
        """Test registration with invalid email."""
        user, error = auth_service.register(
            email="invalid-email",
            password="password123",
            username="Test User",
        )

        assert user is None
        assert "メールアドレス" in error

    def test_register_invalid_password(self, auth_service, db_session):
        """Test registration with invalid password."""
        user, error = auth_service.register(
            email="test@example.com",
            password="short",
            username="Test User",
        )

        assert user is None
        assert "パスワード" in error


class TestAuthServiceLogin:
    """Test cases for AuthService login."""

    @pytest.fixture
    def auth_service(self, db_session):
        """Create AuthService instance."""
        return AuthService()

    @pytest.fixture
    def existing_user(self, auth_service, db_session):
        """Create existing user for login tests."""
        user, _ = auth_service.register(
            email="existing@example.com",
            password="password123",
            username="Existing User",
        )
        return user

    def test_login_success(self, auth_service, existing_user, app):
        """Test successful login."""
        with app.test_request_context():
            user, error = auth_service.login("existing@example.com", "password123")

            assert error is None
            assert user is not None
            assert user.email == "existing@example.com"

    def test_login_wrong_password(self, auth_service, existing_user, app):
        """Test login with wrong password."""
        with app.test_request_context():
            user, error = auth_service.login("existing@example.com", "wrongpassword")

            assert user is None
            assert "正しくありません" in error

    def test_login_nonexistent_user(self, auth_service, db_session, app):
        """Test login with nonexistent user."""
        with app.test_request_context():
            user, error = auth_service.login("nonexistent@example.com", "password123")

            assert user is None
            assert "正しくありません" in error

    def test_login_empty_credentials(self, auth_service, db_session, app):
        """Test login with empty credentials."""
        with app.test_request_context():
            user, error = auth_service.login("", "")

            assert user is None
            assert "必須です" in error

    def test_login_inactive_user(self, auth_service, existing_user, db_session, app):
        """Test login with inactive user."""
        existing_user.is_active = False
        db_session.commit()

        with app.test_request_context():
            user, error = auth_service.login("existing@example.com", "password123")

            assert user is None
            assert "無効化" in error
