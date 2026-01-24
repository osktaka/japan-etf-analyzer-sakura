"""Tests for Favorite model."""
import pytest

from src.models import Category, ETF, Favorite, User


class TestFavoriteModel:
    """Test cases for Favorite model."""

    @pytest.fixture
    def user(self, db_session):
        """Create test user."""
        user = User(email="test@example.com", username="Test User")
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

    def test_create_favorite(self, db_session, user, etf):
        """Test favorite creation."""
        favorite = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite)
        db_session.commit()

        assert favorite.id is not None
        assert favorite.user_id == user.id
        assert favorite.etf_code == etf.code
        assert favorite.created_at is not None

    def test_favorite_to_dict(self, db_session, user, etf):
        """Test favorite to_dict method."""
        favorite = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite)
        db_session.commit()

        data = favorite.to_dict()

        assert "id" in data
        assert data["user_id"] == user.id
        assert data["etf_code"] == etf.code
        assert "created_at" in data

    def test_unique_constraint(self, db_session, user, etf):
        """Test unique constraint on user_id + etf_code."""
        favorite1 = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite1)
        db_session.commit()

        favorite2 = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite2)

        with pytest.raises(Exception):
            db_session.commit()

    def test_user_relationship(self, db_session, user, etf):
        """Test relationship with User."""
        favorite = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite)
        db_session.commit()

        assert favorite.user.id == user.id
        assert favorite.user.email == user.email

    def test_etf_relationship(self, db_session, user, etf):
        """Test relationship with ETF."""
        favorite = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite)
        db_session.commit()

        assert favorite.etf.code == etf.code
        assert favorite.etf.name == etf.name

    def test_cascade_delete_user(self, db_session, user, etf):
        """Test cascade delete when user is deleted."""
        favorite = Favorite(user_id=user.id, etf_code=etf.code)
        db_session.add(favorite)
        db_session.commit()

        favorite_id = favorite.id

        # Delete user
        db_session.delete(user)
        db_session.commit()

        # Favorite should be deleted
        deleted_favorite = db_session.get(Favorite, favorite_id)
        assert deleted_favorite is None

    def test_favorite_repr(self, db_session, user, etf):
        """Test favorite string representation."""
        favorite = Favorite(user_id=user.id, etf_code=etf.code)
        expected = f"<Favorite user_id={user.id} etf_code={etf.code}>"
        assert repr(favorite) == expected
