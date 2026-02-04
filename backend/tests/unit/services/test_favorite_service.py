"""Tests for FavoriteService."""
import pytest

from src.models import Category, ETF, User
from src.services.favorite_service import FavoriteService


class TestFavoriteService:
    """Test cases for FavoriteService."""

    @pytest.fixture
    def user(self, db_session):
        """Create test user."""
        user = User(user_id="testuser", username="Test User")
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()
        return user

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
    def favorite_service(self, db_session):
        """Create FavoriteService instance."""
        return FavoriteService()

    def test_add_favorite_success(self, favorite_service, user, etf):
        """Test adding favorite successfully."""
        favorite, error = favorite_service.add_favorite(user.id, etf.code)

        assert error is None
        assert favorite is not None
        assert favorite.user_id == user.id
        assert favorite.etf_code == etf.code

    def test_add_favorite_duplicate(self, favorite_service, user, etf, db_session):
        """Test adding duplicate favorite."""
        # Add first time
        favorite_service.add_favorite(user.id, etf.code)

        # Try to add again
        favorite, error = favorite_service.add_favorite(user.id, etf.code)

        assert favorite is None
        assert "既にお気に入り" in error

    def test_add_favorite_nonexistent_etf(self, favorite_service, user):
        """Test adding favorite for nonexistent ETF."""
        favorite, error = favorite_service.add_favorite(user.id, "9999")

        assert favorite is None
        assert "ETFが見つかりません" in error

    def test_remove_favorite_success(self, favorite_service, user, etf, db_session):
        """Test removing favorite successfully."""
        # Add favorite first
        favorite_service.add_favorite(user.id, etf.code)

        # Remove
        success, error = favorite_service.remove_favorite(user.id, etf.code)

        assert error is None
        assert success is True
        assert not favorite_service.is_favorited(user.id, etf.code)

    def test_remove_favorite_not_exists(self, favorite_service, user, etf):
        """Test removing non-existent favorite."""
        success, error = favorite_service.remove_favorite(user.id, etf.code)

        assert success is False
        assert "登録されていません" in error

    def test_get_user_favorites(self, favorite_service, user, etf, etf2, db_session):
        """Test getting user favorites."""
        # Add favorites
        favorite_service.add_favorite(user.id, etf.code)
        favorite_service.add_favorite(user.id, etf2.code)

        favorites = favorite_service.get_user_favorites(user.id)

        assert len(favorites) == 2
        etf_codes = [f["etf_code"] for f in favorites]
        assert etf.code in etf_codes
        assert etf2.code in etf_codes
        # Should include ETF data
        assert "etf" in favorites[0]
        assert favorites[0]["etf"]["name"] is not None

    def test_get_user_favorites_empty(self, favorite_service, user):
        """Test getting favorites when user has none."""
        favorites = favorite_service.get_user_favorites(user.id)

        assert favorites == []

    def test_is_favorited_true(self, favorite_service, user, etf, db_session):
        """Test is_favorited returns true for favorited ETF."""
        favorite_service.add_favorite(user.id, etf.code)

        assert favorite_service.is_favorited(user.id, etf.code) is True

    def test_is_favorited_false(self, favorite_service, user, etf):
        """Test is_favorited returns false for non-favorited ETF."""
        assert favorite_service.is_favorited(user.id, etf.code) is False

    def test_get_favorite_codes(self, favorite_service, user, etf, etf2, db_session):
        """Test getting list of favorited ETF codes."""
        favorite_service.add_favorite(user.id, etf.code)
        favorite_service.add_favorite(user.id, etf2.code)

        codes = favorite_service.get_favorite_codes(user.id)

        assert len(codes) == 2
        assert etf.code in codes
        assert etf2.code in codes

    def test_get_favorite_codes_empty(self, favorite_service, user):
        """Test getting codes when user has no favorites."""
        codes = favorite_service.get_favorite_codes(user.id)

        assert codes == []
