"""Tests for CompareService."""
from datetime import datetime

from src.models import PerformanceCache
from src.services.compare_service import CompareService


class TestCompareServiceBatchPerformance:
    """Test cases for CompareService.get_batch_performance()."""

    def test_get_batch_performance_from_cache(self, db_session):
        """Test getting batch performance from cache."""
        # Setup cache data
        entries = [
            PerformanceCache(etf_code="1306", period="1m", return_rate=4.78),
            PerformanceCache(etf_code="1306", period="1y", return_rate=35.92),
            PerformanceCache(etf_code="1348", period="1m", return_rate=5.12),
            PerformanceCache(etf_code="1348", period="1y", return_rate=35.96),
        ]
        for entry in entries:
            entry.calculated_at = datetime.utcnow()
            db_session.add(entry)
        db_session.commit()

        # Test
        service = CompareService()
        result = service.get_batch_performance(["1306", "1348"])

        assert "1306" in result
        assert "1348" in result
        assert result["1306"]["1m"] == 4.78
        assert result["1306"]["1y"] == 35.92
        assert result["1348"]["1m"] == 5.12

    def test_get_batch_performance_missing_code(self, db_session):
        """Test getting batch performance for code not in cache."""
        # Setup cache data for only one code
        cache = PerformanceCache(
            etf_code="1306",
            period="1m",
            return_rate=4.78,
            calculated_at=datetime.utcnow(),
        )
        db_session.add(cache)
        db_session.commit()

        # Test with a code not in cache
        service = CompareService()
        result = service.get_batch_performance(["1306", "9999"])

        assert result["1306"] == {"1m": 4.78}
        assert result["9999"] == {}  # Empty dict for missing code

    def test_get_batch_performance_limit_50(self, db_session):
        """Test that batch performance limits to 50 codes."""
        service = CompareService()
        codes = [str(i) for i in range(100)]

        result = service.get_batch_performance(codes)

        # Should only return 50 codes
        assert len(result) == 50

    def test_get_batch_performance_null_return_rate(self, db_session):
        """Test handling null return rates in cache."""
        cache = PerformanceCache(
            etf_code="1306",
            period="20y",
            return_rate=None,
            calculated_at=datetime.utcnow(),
        )
        db_session.add(cache)
        db_session.commit()

        service = CompareService()
        result = service.get_batch_performance(["1306"])

        assert result["1306"]["20y"] is None
