"""Tests for AuthService."""
import pytest

from src.services.auth_service import AuthService


class TestAuthServiceValidation:
    """Test cases for AuthService validation."""

    @pytest.fixture
    def auth_service(self, db_session):
        """Create AuthService instance."""
        return AuthService()

    def test_validate_user_id_valid(self, auth_service):
        """Test valid user_id validation."""
        valid, error = auth_service.validate_user_id("testuser123")
        assert valid is True
        assert error is None

    def test_validate_user_id_empty(self, auth_service):
        """Test empty user_id validation."""
        valid, error = auth_service.validate_user_id("")
        assert valid is False
        assert error == "ユーザーIDは必須です"

    def test_validate_user_id_invalid_format(self, auth_service):
        """Test invalid user_id format."""
        valid, error = auth_service.validate_user_id("ab")  # too short
        assert valid is False
        assert "3〜50文字" in error

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

    def test_register_success(self, auth_service, db_session, app):
        """Test successful user registration."""
        with app.test_request_context():
            user, error = auth_service.register(
                user_id="newuser123",
                password="password123",
                username="New User",
            )

            assert error is None
            assert user is not None
            assert user.user_id == "newuser123"
            assert user.username == "New User"
            assert user.id is not None

    def test_register_duplicate_user_id(self, auth_service, db_session, app):
        """Test registration with duplicate user_id."""
        with app.test_request_context():
            # First registration
            auth_service.register(
                user_id="testuser",
                password="password123",
                username="User 1",
            )

            # Second registration with same user_id
            user, error = auth_service.register(
                user_id="testuser",
                password="password456",
                username="User 2",
            )

            assert user is None
            assert error == "このユーザーIDは既に登録されています"

    def test_register_invalid_user_id(self, auth_service, db_session, app):
        """Test registration with invalid user_id."""
        with app.test_request_context():
            user, error = auth_service.register(
                user_id="ab",  # too short
                password="password123",
                username="Test User",
            )

            assert user is None
            assert "ユーザーID" in error

    def test_register_invalid_password(self, auth_service, db_session, app):
        """Test registration with invalid password."""
        with app.test_request_context():
            user, error = auth_service.register(
                user_id="testuser",
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
    def existing_user(self, auth_service, db_session, app):
        """Create existing user for login tests."""
        with app.test_request_context():
            user, _ = auth_service.register(
                user_id="existinguser",
                password="password123",
                username="Existing User",
            )
            return user

    def test_login_success(self, auth_service, existing_user, app):
        """Test successful login."""
        with app.test_request_context():
            user, error = auth_service.login("existinguser", "password123")

            assert error is None
            assert user is not None
            assert user.user_id == "existinguser"

    def test_login_wrong_password(self, auth_service, existing_user, app):
        """Test login with wrong password."""
        with app.test_request_context():
            user, error = auth_service.login("existinguser", "wrongpassword")

            assert user is None
            assert "正しくありません" in error

    def test_login_nonexistent_user(self, auth_service, db_session, app):
        """Test login with nonexistent user."""
        with app.test_request_context():
            user, error = auth_service.login("nonexistent", "password123")

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
            user, error = auth_service.login("existinguser", "password123")

            assert user is None
            assert "無効化" in error

    def test_login_demo_user_rejected(self, auth_service, db_session, app):
        """demoユーザーは通常ログイン経路から拒否される（存在有無に関わらず）."""
        with app.test_request_context():
            user, error = auth_service.login("demo", "anypassword")

            assert user is None
            assert "正しくありません" in error


class TestAuthServiceChangePassword:
    """Test cases for AuthService change_password."""

    @pytest.fixture
    def auth_service(self, db_session):
        """Create AuthService instance."""
        return AuthService()

    @pytest.fixture
    def existing_user(self, auth_service, db_session, app):
        """Create existing user for change password tests."""
        with app.test_request_context():
            user, _ = auth_service.register(
                user_id="passworduser",
                password="password123",
                username="Password User",
            )
            return user

    def test_change_password_success(
        self, auth_service, existing_user, db_session, app
    ):
        """Test successful password change."""
        with app.test_request_context():
            success, error = auth_service.change_password(
                existing_user, "password123", "newpassword123"
            )

            assert success is True
            assert error is None
            # Verify new password works
            assert existing_user.check_password("newpassword123")
            # Verify old password no longer works
            assert not existing_user.check_password("password123")

    def test_change_password_wrong_current(
        self, auth_service, existing_user, db_session, app
    ):
        """Test password change with wrong current password."""
        with app.test_request_context():
            success, error = auth_service.change_password(
                existing_user, "wrongpassword", "newpassword123"
            )

            assert success is False
            assert "現在のパスワードが正しくありません" in error

    def test_change_password_short_new(
        self, auth_service, existing_user, db_session, app
    ):
        """Test password change with new password too short."""
        with app.test_request_context():
            success, error = auth_service.change_password(
                existing_user, "password123", "short"
            )

            assert success is False
            assert "8文字以上" in error
