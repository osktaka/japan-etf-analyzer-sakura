"""Tests for Category model."""
import pytest

from src.models import Category


class TestCategory:
    """Test cases for Category model."""

    def test_create_category(self, db_session):
        """Test creating a category."""
        category = Category(
            name="国内株式",
            description="日本国内の株式に投資するETF",
            sort_order=1,
        )
        db_session.add(category)
        db_session.commit()

        assert category.id is not None
        assert category.name == "国内株式"
        assert category.description == "日本国内の株式に投資するETF"
        assert category.sort_order == 1
        assert category.created_at is not None
        assert category.updated_at is not None

    def test_category_repr(self, db_session):
        """Test category string representation."""
        category = Category(name="国内株式", sort_order=1)
        db_session.add(category)
        db_session.commit()

        assert "国内株式" in repr(category)

    def test_category_to_dict(self, db_session):
        """Test converting category to dictionary."""
        category = Category(
            name="国内株式",
            description="日本国内の株式に投資するETF",
            sort_order=1,
        )
        db_session.add(category)
        db_session.commit()

        data = category.to_dict()

        assert data["id"] == category.id
        assert data["name"] == "国内株式"
        assert data["description"] == "日本国内の株式に投資するETF"
        assert data["sort_order"] == 1

    def test_category_unique_name(self, db_session):
        """Test that category names must be unique."""
        category1 = Category(name="国内株式", sort_order=1)
        db_session.add(category1)
        db_session.commit()

        category2 = Category(name="国内株式", sort_order=2)
        db_session.add(category2)

        with pytest.raises(Exception):
            db_session.commit()
