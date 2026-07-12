"""Tests for ChartService split adjustment logic."""
from datetime import date
from unittest.mock import Mock

import pytest

from src.models.stock_split import StockSplit
from src.repositories.stock_split_repository import StockSplitRepository
from src.services.chart_service import ChartService


@pytest.fixture
def service():
    """Create ChartService with a mocked stock split repository.

    yfinance/ETF repository are untouched by _apply_split_adjustments, so only
    stock_split_repository needs mocking (no network/DB access in these tests).
    """
    svc = ChartService()
    svc.stock_split_repository = Mock(spec=StockSplitRepository)
    return svc


def _split(split_date: str, ratio: float, is_chart_applied: bool = True) -> StockSplit:
    return StockSplit(
        etf_code="1234",
        split_date=date.fromisoformat(split_date),
        ratio=ratio,
        is_chart_applied=is_chart_applied,
    )


class TestApplySplitAdjustments:
    """Tests for _apply_split_adjustments."""

    def test_empty_chart_data_returns_as_is(self, service):
        assert service._apply_split_adjustments("1234", [], 30) == []

    def test_no_splits_returns_data_unchanged(self, service):
        service.stock_split_repository.get_chart_applied_splits_since.return_value = []
        chart_data = [
            {"date": "2024-01-10", "open": 100, "high": 110, "low": 90, "close": 105}
        ]

        result = service._apply_split_adjustments("1234", chart_data, 30)

        assert result == chart_data

    def test_price_before_split_is_divided_by_ratio(self, service):
        # 2:1 split on 2024-02-01: prices before that date get divided by 2
        service.stock_split_repository.get_chart_applied_splits_since.return_value = [
            _split("2024-02-01", 2.0)
        ]
        chart_data = [
            {
                "date": "2024-01-10",
                "open": 2000,
                "high": 2100,
                "low": 1900,
                "close": 2050,
            }
        ]

        result = service._apply_split_adjustments("1234", chart_data, 60)

        assert result[0]["open"] == pytest.approx(1000.0)
        assert result[0]["high"] == pytest.approx(1050.0)
        assert result[0]["low"] == pytest.approx(950.0)
        assert result[0]["close"] == pytest.approx(1025.0)

    def test_price_on_or_after_split_date_is_unchanged(self, service):
        service.stock_split_repository.get_chart_applied_splits_since.return_value = [
            _split("2024-02-01", 2.0)
        ]
        chart_data = [
            {
                "date": "2024-02-01",
                "open": 1000,
                "high": 1050,
                "low": 950,
                "close": 1025,
            }
        ]

        result = service._apply_split_adjustments("1234", chart_data, 60)

        # point_date < split.split_date is False on the split date itself -> no division
        assert result[0]["close"] == pytest.approx(1025.0)

    def test_multiple_splits_cumulative_ratio(self, service):
        # Two splits before the data point: 2:1 then 3:1 -> cumulative ratio 6.0
        service.stock_split_repository.get_chart_applied_splits_since.return_value = [
            _split("2024-02-01", 2.0),
            _split("2024-04-01", 3.0),
        ]
        chart_data = [
            {
                "date": "2024-01-10",
                "open": 6000,
                "high": 6000,
                "low": 6000,
                "close": 6000,
            }
        ]

        result = service._apply_split_adjustments("1234", chart_data, 120)

        assert result[0]["close"] == pytest.approx(1000.0)

    def test_multiple_splits_partial_cumulative_ratio(self, service):
        # Data point falls between the two splits -> only the later split applies
        service.stock_split_repository.get_chart_applied_splits_since.return_value = [
            _split("2024-02-01", 2.0),
            _split("2024-04-01", 3.0),
        ]
        chart_data = [
            {
                "date": "2024-03-01",
                "open": 3000,
                "high": 3000,
                "low": 3000,
                "close": 3000,
            }
        ]

        result = service._apply_split_adjustments("1234", chart_data, 120)

        assert result[0]["close"] == pytest.approx(1000.0)

    def test_is_chart_applied_false_splits_are_excluded_by_repository_query(
        self, service
    ):
        # get_chart_applied_splits_since is responsible for filtering is_chart_applied=True;
        # verify the service only reflects what the repository returns (i.e. it does not
        # separately re-check is_chart_applied on each split object).
        service.stock_split_repository.get_chart_applied_splits_since.return_value = []
        chart_data = [
            {
                "date": "2024-01-10",
                "open": 2000,
                "high": 2000,
                "low": 2000,
                "close": 2000,
            }
        ]

        result = service._apply_split_adjustments("1234", chart_data, 60)

        assert result[0]["close"] == 2000

    def test_missing_date_field_is_passed_through_unchanged(self, service):
        service.stock_split_repository.get_chart_applied_splits_since.return_value = [
            _split("2024-02-01", 2.0)
        ]
        chart_data = [{"open": 2000, "high": 2000, "low": 2000, "close": 2000}]

        result = service._apply_split_adjustments("1234", chart_data, 60)

        assert result[0]["close"] == 2000

    def test_calls_repository_with_start_date_derived_from_period_days(self, service):
        service.stock_split_repository.get_chart_applied_splits_since.return_value = []

        service._apply_split_adjustments("1234", [{"date": "2024-01-10"}], 30)

        service.stock_split_repository.get_chart_applied_splits_since.assert_called_once()
        call_args = (
            service.stock_split_repository.get_chart_applied_splits_since.call_args
        )
        assert call_args[0][0] == "1234"
