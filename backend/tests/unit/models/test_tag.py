"""Tests for Tag model."""
import pytest

from src.models import Tag


class TestTag:
    """Test cases for Tag model."""

    def test_create_tag(self, db_session):
        """Test creating a tag."""
        tag = Tag(name="高配当", color="#10B981")
        db_session.add(tag)
        db_session.commit()

        assert tag.id is not None
        assert tag.name == "高配当"
        assert tag.color == "#10B981"
        assert tag.created_at is not None
        assert tag.updated_at is not None

    def test_tag_default_color(self, db_session):
        """Test tag default color."""
        tag = Tag(name="低コスト")
        db_session.add(tag)
        db_session.commit()

        assert tag.color == "#6B7280"

    def test_tag_repr(self, db_session):
        """Test tag string representation."""
        tag = Tag(name="高配当")
        db_session.add(tag)
        db_session.commit()

        assert "高配当" in repr(tag)

    def test_tag_to_dict(self, db_session):
        """Test converting tag to dictionary."""
        tag = Tag(name="高配当", color="#10B981")
        db_session.add(tag)
        db_session.commit()

        data = tag.to_dict()

        assert data["id"] == tag.id
        assert data["name"] == "高配当"
        assert data["color"] == "#10B981"

    def test_tag_unique_name(self, db_session):
        """Test that tag names must be unique."""
        tag1 = Tag(name="高配当")
        db_session.add(tag1)
        db_session.commit()

        tag2 = Tag(name="高配当")
        db_session.add(tag2)

        with pytest.raises(Exception):
            db_session.commit()
