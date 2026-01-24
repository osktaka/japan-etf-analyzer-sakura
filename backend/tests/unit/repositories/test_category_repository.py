"""Tests for CategoryRepository."""
import pytest

from src.models import Category
from src.repositories import CategoryRepository


class TestCategoryRepository:
    """Test cases for CategoryRepository."""

    def test_create_category(self, db_session):
        """Test creating a category."""
        repo = CategoryRepository()
        category = Category(name="国内株式", sort_order=1)
        result = repo.create(category)

        assert result.id is not None
        assert result.name == "国内株式"

    def test_get_by_id(self, db_session):
        """Test getting category by ID."""
        repo = CategoryRepository()
        category = Category(name="外国株式", sort_order=2)
        repo.create(category)

        result = repo.get_by_id(category.id)

        assert result is not None
        assert result.name == "外国株式"

    def test_get_by_name(self, db_session):
        """Test getting category by name."""
        repo = CategoryRepository()
        category = Category(name="REIT", sort_order=5)
        repo.create(category)

        result = repo.get_by_name("REIT")

        assert result is not None
        assert result.sort_order == 5

    def test_get_by_name_not_found(self, db_session):
        """Test getting non-existent category by name."""
        repo = CategoryRepository()
        result = repo.get_by_name("存在しない")

        assert result is None

    def test_get_all_sorted(self, db_session):
        """Test getting all categories sorted."""
        repo = CategoryRepository()
        repo.create(Category(name="C", sort_order=3))
        repo.create(Category(name="A", sort_order=1))
        repo.create(Category(name="B", sort_order=2))

        results = repo.get_all_sorted()

        assert len(results) == 3
        assert results[0].name == "A"
        assert results[1].name == "B"
        assert results[2].name == "C"

    def test_create_if_not_exists_new(self, db_session):
        """Test create_if_not_exists with new category."""
        repo = CategoryRepository()
        result = repo.create_if_not_exists(
            name="新カテゴリ", description="説明", sort_order=10
        )

        assert result is not None
        assert result.name == "新カテゴリ"
        assert result.description == "説明"

    def test_create_if_not_exists_existing(self, db_session):
        """Test create_if_not_exists with existing category."""
        repo = CategoryRepository()
        original = repo.create(
            Category(name="既存", description="元の説明", sort_order=5)
        )

        result = repo.create_if_not_exists(
            name="既存", description="新しい説明", sort_order=99
        )

        assert result.id == original.id
        assert result.description == "元の説明"
