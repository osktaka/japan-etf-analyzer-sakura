"""Tests for TagRepository."""

from src.models import Tag
from src.repositories import TagRepository


class TestTagRepository:
    """Test cases for TagRepository."""

    def test_create_tag(self, db_session):
        """Test creating a tag."""
        repo = TagRepository()
        tag = Tag(name="高配当", color="#10B981")
        result = repo.create(tag)

        assert result.id is not None
        assert result.name == "高配当"

    def test_get_by_name(self, db_session):
        """Test getting tag by name."""
        repo = TagRepository()
        tag = Tag(name="低コスト", color="#3B82F6")
        repo.create(tag)

        result = repo.get_by_name("低コスト")

        assert result is not None
        assert result.color == "#3B82F6"

    def test_get_by_names(self, db_session):
        """Test getting tags by list of names."""
        repo = TagRepository()
        repo.create(Tag(name="タグA"))
        repo.create(Tag(name="タグB"))
        repo.create(Tag(name="タグC"))

        results = repo.get_by_names(["タグA", "タグC"])

        assert len(results) == 2
        names = [t.name for t in results]
        assert "タグA" in names
        assert "タグC" in names

    def test_get_all_sorted(self, db_session):
        """Test getting all tags sorted by name."""
        repo = TagRepository()
        repo.create(Tag(name="Zebra"))
        repo.create(Tag(name="Alpha"))
        repo.create(Tag(name="Beta"))

        results = repo.get_all_sorted()

        assert len(results) == 3
        assert results[0].name == "Alpha"
        assert results[1].name == "Beta"
        assert results[2].name == "Zebra"

    def test_create_if_not_exists_new(self, db_session):
        """Test create_if_not_exists with new tag."""
        repo = TagRepository()
        result = repo.create_if_not_exists(name="新タグ", color="#FF0000")

        assert result is not None
        assert result.name == "新タグ"
        assert result.color == "#FF0000"

    def test_create_if_not_exists_existing(self, db_session):
        """Test create_if_not_exists with existing tag."""
        repo = TagRepository()
        original = repo.create(Tag(name="既存タグ", color="#000000"))

        result = repo.create_if_not_exists(name="既存タグ", color="#FFFFFF")

        assert result.id == original.id
        assert result.color == "#000000"
