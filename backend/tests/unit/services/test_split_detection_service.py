"""Tests for SplitDetectionService."""
from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.models import StockSplit
from src.repositories import StockSplitRepository
from src.services.split_detection_service import SplitDetectionService


@pytest.fixture
def mock_repository():
    return Mock(spec=StockSplitRepository)


@pytest.fixture
def service(mock_repository):
    svc = SplitDetectionService()
    svc.repository = mock_repository
    return svc


def _mock_yf_splits(ratio: float, split_date: str = "2024-02-01"):
    """Build a pandas Series shaped like yfinance's Ticker.splits."""
    return pd.Series([ratio], index=pd.to_datetime([split_date]))


class TestCheckForSplitsThreshold:
    """Boundary tests for PRICE_CHANGE_THRESHOLD (30.0%)."""

    def test_change_below_threshold_returns_none_without_yfinance_call(self, service):
        # +29.9% change: below threshold -> short-circuits before touching yfinance
        with patch("yfinance.Ticker") as mock_ticker:
            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=129.9,
                current_date=date(2024, 2, 1),
            )

            assert result is None
            mock_ticker.assert_not_called()

    def test_change_exactly_at_threshold_proceeds_to_yfinance(self, service):
        # +30.0% change: "< 30.0" is False at the boundary -> proceeds
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = _mock_yf_splits(2.0)
            mock_ticker.return_value = mock_stock
            service.repository.exists.return_value = False

            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=130.0,
                current_date=date(2024, 2, 1),
            )

            assert result is not None
            assert result.ratio == 2.0
            mock_ticker.assert_called_once_with("1234.T")

    def test_change_above_threshold_proceeds_to_yfinance(self, service):
        # +30.1% change: clearly above threshold -> proceeds
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = _mock_yf_splits(2.0)
            mock_ticker.return_value = mock_stock
            service.repository.exists.return_value = False

            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=130.1,
                current_date=date(2024, 2, 1),
            )

            assert result is not None

    def test_negative_change_beyond_threshold_proceeds(self, service):
        # Reverse split scenario: large negative change also crosses the threshold
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = _mock_yf_splits(0.5)
            mock_ticker.return_value = mock_stock
            service.repository.exists.return_value = False

            result = service.check_for_splits(
                "1234",
                previous_close=200.0,
                current_close=100.0,
                current_date=date(2024, 2, 1),
            )

            assert result is not None
            assert result.ratio == 0.5


class TestCheckForSplitsGuardsAndFallback:
    def test_previous_close_zero_returns_none_without_yfinance_call(self, service):
        with patch("yfinance.Ticker") as mock_ticker:
            result = service.check_for_splits(
                "1234",
                previous_close=0.0,
                current_close=100.0,
                current_date=date(2024, 2, 1),
            )

            assert result is None
            mock_ticker.assert_not_called()

    def test_already_registered_split_returns_none(self, service):
        # Large price change + yfinance confirms a split, but it's already registered
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = _mock_yf_splits(2.0, "2024-02-01")
            mock_ticker.return_value = mock_stock
            service.repository.exists.return_value = True

            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=200.0,
                current_date=date(2024, 2, 1),
            )

            assert result is None
            service.repository.exists.assert_called_once_with("1234", date(2024, 2, 1))

    def test_yfinance_no_splits_returns_none(self, service):
        # Large price change but yfinance reports no split history at all
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = pd.Series([], dtype=float)
            mock_ticker.return_value = mock_stock

            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=200.0,
                current_date=date(2024, 2, 1),
            )

            assert result is None

    def test_yfinance_exception_returns_none(self, service):
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("network error")

            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=200.0,
                current_date=date(2024, 2, 1),
            )

            assert result is None

    def test_detected_split_has_is_applied_false(self, service):
        # Newly detected splits must default to unreviewed (is_applied=False)
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = _mock_yf_splits(2.0)
            mock_ticker.return_value = mock_stock
            service.repository.exists.return_value = False

            result = service.check_for_splits(
                "1234",
                previous_close=100.0,
                current_close=200.0,
                current_date=date(2024, 2, 1),
            )

            assert result.is_applied is False
            assert result.previous_close == 100.0
            assert result.current_close == 200.0


class TestRegisterSplit:
    def _pending_split(self):
        return StockSplit(
            etf_code="1234",
            split_date=date(2024, 2, 1),
            ratio=2.0,
            is_applied=False,
        )

    def test_register_success(self, service):
        service.repository.exists.return_value = False
        created = self._pending_split()
        created.id = 1
        service.repository.create.return_value = created

        result = service.register_split(self._pending_split())

        assert result is created
        service.repository.create.assert_called_once()

    def test_register_duplicate_skips_create(self, service):
        service.repository.exists.return_value = True

        result = service.register_split(self._pending_split())

        assert result is None
        service.repository.create.assert_not_called()

    def test_register_repository_exception_returns_none(self, service):
        service.repository.exists.return_value = False
        service.repository.create.side_effect = Exception("db error")

        result = service.register_split(self._pending_split())

        assert result is None
