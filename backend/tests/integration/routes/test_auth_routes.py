"""Integration tests for authentication routes."""
import pytest



class TestAuthRegister:
    """Test cases for POST /api/v1/auth/register."""

    def test_register_success(self, client, db_session):
        """Test successful registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "username": "New User",
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["email"] == "newuser@example.com"
        assert data["data"]["username"] == "New User"
        assert "message" in data

    def test_register_missing_fields(self, client, db_session):
        """Test registration with missing fields."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_register_invalid_email(self, client, db_session):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "password123",
                "username": "Test User",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_register_duplicate_email(self, client, db_session):
        """Test registration with duplicate email."""
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "username": "User 1",
            },
        )

        # Second registration with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password456",
                "username": "User 2",
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "既に登録" in data["error"]["message"]

    def test_register_no_body(self, client, db_session):
        """Test registration without request body."""
        response = client.post(
            "/api/v1/auth/register",
            content_type="application/json",
        )

        assert response.status_code == 400


class TestAuthLogin:
    """Test cases for POST /api/v1/auth/login."""

    @pytest.fixture
    def registered_user(self, client, db_session):
        """Create a registered user for login tests."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "username": "Test User",
            },
        )

    def test_login_success(self, client, registered_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client, registered_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

    def test_login_nonexistent_user(self, client, db_session):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )

        assert response.status_code == 401

    def test_login_no_body(self, client, db_session):
        """Test login without request body."""
        response = client.post(
            "/api/v1/auth/login",
            content_type="application/json",
        )

        assert response.status_code == 400


class TestAuthLogout:
    """Test cases for POST /api/v1/auth/logout."""

    @pytest.fixture
    def logged_in_client(self, client, db_session):
        """Create a logged-in client."""
        # Register
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "username": "Test User",
            },
        )
        # Login
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        return client

    def test_logout_success(self, logged_in_client):
        """Test successful logout."""
        response = logged_in_client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_logout_not_logged_in(self, client, db_session):
        """Test logout when not logged in."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestAuthMe:
    """Test cases for GET /api/v1/auth/me."""

    @pytest.fixture
    def logged_in_client(self, client, db_session):
        """Create a logged-in client."""
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "password123",
                "username": "Test User",
            },
        )
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        return client

    def test_get_current_user_success(self, logged_in_client):
        """Test getting current user."""
        response = logged_in_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["username"] == "Test User"

    def test_get_current_user_not_logged_in(self, client, db_session):
        """Test getting current user when not logged in."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
