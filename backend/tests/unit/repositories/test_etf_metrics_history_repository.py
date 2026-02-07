"""Tests for EtfMetricsHistoryRepository."""
from datetime import date

from src.models import EtfMetricsHistory
from src.repositories import EtfMetricsHistoryRepository


class TestEtfMetricsHistoryRepository:
    """Test cases for EtfMetricsHistoryRepository."""

    def test_upsert_insert_with_momentum_fields(self, db_session):
        """Test upsert creates new record with momentum fields."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        result = repo.upsert(
            etf_code="1306",
            target_date=target_date,
            dividend_yield=2.5,
            expense_ratio=0.066,
            total_assets=1000000,
            deviation_rate=0.1,
            return_1y=10.5,
            return_3y=30.2,
            volatility=15.0,
            momentum_label="上昇加速",
            regression_rate_1m=5.2,
            regression_rate_3m=12.8,
        )

        assert result.etf_code == "1306"
        assert result.date == target_date
        assert result.momentum_label == "上昇加速"
        assert result.regression_rate_1m == 5.2
        assert result.regression_rate_3m == 12.8

    def test_upsert_update_momentum_fields(self, db_session):
        """Test upsert updates existing record's momentum fields."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        # Insert initial record
        repo.upsert(
            etf_code="1306",
            target_date=target_date,
            momentum_label="横ばい",
            regression_rate_1m=1.0,
            regression_rate_3m=3.0,
        )

        # Update with new momentum data
        result = repo.upsert(
            etf_code="1306",
            target_date=target_date,
            momentum_label="上昇加速",
            regression_rate_1m=5.2,
            regression_rate_3m=12.8,
        )

        assert result.momentum_label == "上昇加速"
        assert result.regression_rate_1m == 5.2
        assert result.regression_rate_3m == 12.8

        # Verify only one record exists
        count = EtfMetricsHistory.query.filter_by(
            etf_code="1306", date=target_date
        ).count()
        assert count == 1

    def test_bulk_upsert_with_momentum_fields(self, db_session):
        """Test bulk_upsert saves momentum fields for multiple records."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        records = [
            {
                "etf_code": "1306",
                "dividend_yield": 2.5,
                "expense_ratio": 0.066,
                "total_assets": 1000000,
                "deviation_rate": 0.1,
                "return_1y": 10.5,
                "return_3y": 30.2,
                "volatility": 15.0,
                "momentum_label": "上昇加速",
                "regression_rate_1m": 5.2,
                "regression_rate_3m": 12.8,
            },
            {
                "etf_code": "1321",
                "dividend_yield": 1.8,
                "expense_ratio": 0.11,
                "total_assets": 500000,
                "deviation_rate": -0.2,
                "return_1y": 8.0,
                "return_3y": 22.0,
                "volatility": 18.0,
                "momentum_label": "下降減速",
                "regression_rate_1m": -2.1,
                "regression_rate_3m": -5.5,
            },
            {
                "etf_code": "1343",
                "dividend_yield": 3.0,
                "expense_ratio": 0.15,
                "total_assets": 200000,
                "deviation_rate": 0.0,
                "return_1y": None,
                "return_3y": None,
                "volatility": None,
                "momentum_label": None,
                "regression_rate_1m": None,
                "regression_rate_3m": None,
            },
        ]

        count = repo.bulk_upsert(records, target_date)
        assert count == 3

        # Verify momentum fields for each record
        r1 = repo.get_by_date("1306", target_date)
        assert r1.momentum_label == "上昇加速"
        assert r1.regression_rate_1m == 5.2
        assert r1.regression_rate_3m == 12.8

        r2 = repo.get_by_date("1321", target_date)
        assert r2.momentum_label == "下降減速"
        assert r2.regression_rate_1m == -2.1
        assert r2.regression_rate_3m == -5.5

        # Verify None values are handled correctly
        r3 = repo.get_by_date("1343", target_date)
        assert r3.momentum_label is None
        assert r3.regression_rate_1m is None
        assert r3.regression_rate_3m is None

    def test_bulk_upsert_update_momentum_fields(self, db_session):
        """Test bulk_upsert updates existing records' momentum fields."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        # Insert initial records
        initial_records = [
            {
                "etf_code": "1306",
                "momentum_label": "横ばい",
                "regression_rate_1m": 0.5,
                "regression_rate_3m": 1.0,
            },
        ]
        repo.bulk_upsert(initial_records, target_date)

        # Update with new momentum data
        updated_records = [
            {
                "etf_code": "1306",
                "momentum_label": "上昇加速",
                "regression_rate_1m": 5.2,
                "regression_rate_3m": 12.8,
            },
        ]
        count = repo.bulk_upsert(updated_records, target_date)
        assert count == 1

        result = repo.get_by_date("1306", target_date)
        assert result.momentum_label == "上昇加速"
        assert result.regression_rate_1m == 5.2
        assert result.regression_rate_3m == 12.8

    def test_get_by_date(self, db_session):
        """Test get_by_date returns record with momentum fields."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        repo.upsert(
            etf_code="1306",
            target_date=target_date,
            momentum_label="上昇減速",
            regression_rate_1m=3.0,
            regression_rate_3m=8.0,
        )

        result = repo.get_by_date("1306", target_date)

        assert result is not None
        assert result.momentum_label == "上昇減速"
        assert result.regression_rate_1m == 3.0
        assert result.regression_rate_3m == 8.0

    def test_get_by_date_not_found(self, db_session):
        """Test get_by_date returns None for non-existent record."""
        repo = EtfMetricsHistoryRepository()
        result = repo.get_by_date("9999", date(2026, 1, 1))
        assert result is None

    def test_get_metrics_batch_for_date(self, db_session):
        """Test batch retrieval includes momentum fields."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        records = [
            {
                "etf_code": "1306",
                "momentum_label": "上昇加速",
                "regression_rate_1m": 5.2,
                "regression_rate_3m": 12.8,
            },
            {
                "etf_code": "1321",
                "momentum_label": "下降加速",
                "regression_rate_1m": -4.0,
                "regression_rate_3m": -10.0,
            },
        ]
        repo.bulk_upsert(records, target_date)

        result = repo.get_metrics_batch_for_date(
            ["1306", "1321", "9999"], target_date
        )

        assert len(result) == 2
        assert "1306" in result
        assert "1321" in result
        assert "9999" not in result
        assert result["1306"].momentum_label == "上昇加速"
        assert result["1321"].regression_rate_1m == -4.0

    def test_to_dict_includes_momentum_fields(self, db_session):
        """Test to_dict includes momentum fields."""
        repo = EtfMetricsHistoryRepository()
        target_date = date(2026, 2, 7)

        record = repo.upsert(
            etf_code="1306",
            target_date=target_date,
            momentum_label="上昇加速",
            regression_rate_1m=5.2,
            regression_rate_3m=12.8,
        )

        result_dict = record.to_dict()

        assert result_dict["momentum_label"] == "上昇加速"
        assert result_dict["regression_rate_1m"] == 5.2
        assert result_dict["regression_rate_3m"] == 12.8
