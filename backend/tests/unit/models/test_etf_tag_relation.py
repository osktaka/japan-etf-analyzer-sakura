"""Tests for ETFTagRelation model."""
import pytest

from src.models import ETF, ETFTagRelation, Tag


class TestETFTagRelation:
    """Test cases for ETFTagRelation model."""

    def test_create_relation(self, db_session):
        """Test creating an ETF-Tag relation."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        tag = Tag(name="高配当")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation = ETFTagRelation(etf_code=etf.code, tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        assert relation.id is not None
        assert relation.etf_code == "1306"
        assert relation.tag_id == tag.id
        assert relation.created_at is not None

    def test_relation_etf_access(self, db_session):
        """Test accessing ETF from relation."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        tag = Tag(name="高配当")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation = ETFTagRelation(etf_code=etf.code, tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        assert relation.etf.code == "1306"
        assert relation.tag.name == "高配当"

    def test_relation_unique_constraint(self, db_session):
        """Test that same ETF-Tag combination cannot be added twice."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        tag = Tag(name="高配当")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation1 = ETFTagRelation(etf_code=etf.code, tag_id=tag.id)
        db_session.add(relation1)
        db_session.commit()

        relation2 = ETFTagRelation(etf_code=etf.code, tag_id=tag.id)
        db_session.add(relation2)

        with pytest.raises(Exception):
            db_session.commit()

    def test_cascade_delete_from_etf(self, db_session):
        """Test that deleting ETF cascades to relations."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        tag = Tag(name="高配当")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation = ETFTagRelation(etf_code=etf.code, tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        relation_id = relation.id
        db_session.delete(etf)
        db_session.commit()

        deleted_relation = db_session.get(ETFTagRelation, relation_id)
        assert deleted_relation is None

    def test_relation_repr(self, db_session):
        """Test relation string representation."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        tag = Tag(name="高配当")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation = ETFTagRelation(etf_code=etf.code, tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        assert "1306" in repr(relation)
