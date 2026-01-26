"""Tests for PerformanceCache model."""
from datetime import datetime

from src.models import PerformanceCache


class TestPerformanceCache:
    """Test cases for PerformanceCache model."""

    def test_create_performance_cache(self, db_session):
        """Test creating a performance cache entry."""
        cache = PerformanceCache(
            etf_code="1306",
            period="1y",
            return_rate=35.92,
            calculated_at=datetime.utcnow(),
        )
        db_session.add(cache)
        db_session.commit()

        assert cache.id is not None
        assert cache.etf_code == "1306"
        assert cache.period == "1y"
        assert cache.return_rate == 35.92

    def test_unique_constraint(self, db_session):
        """Test unique constraint on etf_code and period."""
        cache1 = PerformanceCache(
            etf_code="1306",
            period="1y",
            return_rate=35.92,
        )
        db_session.add(cache1)
        db_session.commit()

        # Same etf_code and period should fail
        cache2 = PerformanceCache(
            etf_code="1306",
            period="1y",
            return_rate=40.0,
        )
        db_session.add(cache2)

        import pytest
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_null_return_rate(self, db_session):
        """Test that return_rate can be null."""
        cache = PerformanceCache(
            etf_code="1306",
            period="20y",
            return_rate=None,
        )
        db_session.add(cache)
        db_session.commit()

        assert cache.return_rate is None

    def test_to_dict(self, db_session):
        """Test converting to dictionary."""
        now = datetime.utcnow()
        cache = PerformanceCache(
            etf_code="1306",
            period="1y",
            return_rate=35.92,
            calculated_at=now,
        )
        db_session.add(cache)
        db_session.commit()

        data = cache.to_dict()

        assert data["etf_code"] == "1306"
        assert data["period"] == "1y"
        assert data["return_rate"] == 35.92
        assert data["calculated_at"] is not None
