"""Tests for User model."""
import pytest

from src.models import User


class TestUserModel:
    """Test cases for User model."""

    def test_create_user(self, db_session):
        """Test user creation."""
        user = User(user_id="test", username="Test User")
        user.set_password("password123")

        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.user_id == "test"
        assert user.username == "Test User"
        assert user.is_active is True
        assert user.created_at is not None

    def test_password_hashing(self, db_session):
        """Test password is hashed correctly."""
        user = User(user_id="test", username="Test User")
        user.set_password("password123")

        # Password should not be stored in plain text
        assert user.password_hash != "password123"
        assert user.check_password("password123") is True
        assert user.check_password("wrongpassword") is False

    def test_to_dict(self, db_session):
        """Test user to_dict method."""
        user = User(user_id="test", username="Test User")
        user.set_password("password123")

        db_session.add(user)
        db_session.commit()

        data = user.to_dict()

        assert "id" in data
        assert data["user_id"] == "test"
        assert data["username"] == "Test User"
        assert data["is_active"] is True
        assert "created_at" in data
        # Password should not be in to_dict
        assert "password_hash" not in data
        assert "password" not in data

    def test_unique_user_id_constraint(self, db_session):
        """Test unique user_id constraint."""
        user1 = User(user_id="test", username="User 1")
        user1.set_password("password123")
        db_session.add(user1)
        db_session.commit()

        user2 = User(user_id="test", username="User 2")
        user2.set_password("password456")
        db_session.add(user2)

        with pytest.raises(Exception):
            db_session.commit()

    def test_user_repr(self, db_session):
        """Test user string representation."""
        user = User(user_id="test", username="Test User")
        assert repr(user) == "<User test>"
