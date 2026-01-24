"""Integration tests for favorite routes."""
import pytest

from src.models import Category, ETF


class TestFavoriteRoutes:
    """Test cases for favorite API routes."""

    @pytest.fixture
    def category(self, db_session):
        """Create test category."""
        category = Category(name="Test Category")
        db_session.add(category)
        db_session.commit()
        return category

    @pytest.fixture
    def etf(self, db_session, category):
        """Create test ETF."""
        etf = ETF(
            code="1306",
            name="TOPIX連動型上場投資信託",
            category_id=category.id,
        )
        db_session.add(etf)
        db_session.commit()
        return etf

    @pytest.fixture
    def etf2(self, db_session, category):
        """Create second test ETF."""
        etf = ETF(
            code="1305",
            name="ダイワTOPIX",
            category_id=category.id,
        )
        db_session.add(etf)
        db_session.commit()
        return etf

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


class TestGetFavorites(TestFavoriteRoutes):
    """Test cases for GET /api/v1/favorites."""

    def test_get_favorites_empty(self, logged_in_client, etf):
        """Test getting favorites when empty."""
        response = logged_in_client.get("/api/v1/favorites")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == []

    def test_get_favorites_with_data(self, logged_in_client, etf, etf2):
        """Test getting favorites with data."""
        # Add favorites
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf2.code},
        )

        response = logged_in_client.get("/api/v1/favorites")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 2

    def test_get_favorites_not_logged_in(self, client, db_session, etf):
        """Test getting favorites when not logged in."""
        response = client.get("/api/v1/favorites")

        assert response.status_code == 401


class TestAddFavorite(TestFavoriteRoutes):
    """Test cases for POST /api/v1/favorites."""

    def test_add_favorite_success(self, logged_in_client, etf):
        """Test adding favorite successfully."""
        response = logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["etf_code"] == etf.code

    def test_add_favorite_duplicate(self, logged_in_client, etf):
        """Test adding duplicate favorite."""
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )

        response = logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_add_favorite_nonexistent_etf(self, logged_in_client):
        """Test adding favorite for nonexistent ETF."""
        response = logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": "9999"},
        )

        assert response.status_code == 400

    def test_add_favorite_no_etf_code(self, logged_in_client):
        """Test adding favorite without ETF code."""
        response = logged_in_client.post(
            "/api/v1/favorites",
            json={},
        )

        assert response.status_code == 400

    def test_add_favorite_not_logged_in(self, client, db_session, etf):
        """Test adding favorite when not logged in."""
        response = client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )

        assert response.status_code == 401


class TestRemoveFavorite(TestFavoriteRoutes):
    """Test cases for DELETE /api/v1/favorites/{etf_code}."""

    def test_remove_favorite_success(self, logged_in_client, etf):
        """Test removing favorite successfully."""
        # Add first
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )

        response = logged_in_client.delete(f"/api/v1/favorites/{etf.code}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_remove_favorite_not_exists(self, logged_in_client, etf):
        """Test removing non-existent favorite."""
        response = logged_in_client.delete(f"/api/v1/favorites/{etf.code}")

        assert response.status_code == 400

    def test_remove_favorite_not_logged_in(self, client, db_session, etf):
        """Test removing favorite when not logged in."""
        response = client.delete(f"/api/v1/favorites/{etf.code}")

        assert response.status_code == 401


class TestFavoriteCodes(TestFavoriteRoutes):
    """Test cases for GET /api/v1/favorites/codes."""

    def test_get_codes_empty(self, logged_in_client, etf):
        """Test getting codes when empty."""
        response = logged_in_client.get("/api/v1/favorites/codes")

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"] == []

    def test_get_codes_with_data(self, logged_in_client, etf, etf2):
        """Test getting codes with data."""
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf2.code},
        )

        response = logged_in_client.get("/api/v1/favorites/codes")

        assert response.status_code == 200
        data = response.get_json()
        assert etf.code in data["data"]
        assert etf2.code in data["data"]


class TestCheckFavorite(TestFavoriteRoutes):
    """Test cases for GET /api/v1/favorites/check/{etf_code}."""

    def test_check_favorited(self, logged_in_client, etf):
        """Test checking favorited ETF."""
        logged_in_client.post(
            "/api/v1/favorites",
            json={"etf_code": etf.code},
        )

        response = logged_in_client.get(f"/api/v1/favorites/check/{etf.code}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["is_favorited"] is True

    def test_check_not_favorited(self, logged_in_client, etf):
        """Test checking non-favorited ETF."""
        response = logged_in_client.get(f"/api/v1/favorites/check/{etf.code}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["is_favorited"] is False
