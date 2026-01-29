"""Tests for SplitHistoryService."""
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.models import StockSplit
from src.services.split_history_service import SplitHistoryService


class TestSplitHistoryService:
    """Test cases for SplitHistoryService."""

    @pytest.fixture
    def service(self, db_session):
        """Create SplitHistoryService instance."""
        return SplitHistoryService()

    @pytest.fixture
    def mock_splits_data(self):
        """Mock splits data from yfinance."""
        # Create pandas Series with DatetimeIndex
        dates = pd.to_datetime(["2020-01-15", "2021-06-20"])
        ratios = [2.0, 0.5]
        return pd.Series(ratios, index=dates)

    def test_fetch_historical_splits_success(self, service, mock_splits_data):
        """Test fetching historical splits successfully."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = mock_splits_data
            mock_ticker.return_value = mock_stock

            result = service.fetch_historical_splits("1306")

            assert len(result) == 2
            assert result[0]["split_date"] == date(2020, 1, 15)
            assert result[0]["ratio"] == 2.0
            assert result[1]["split_date"] == date(2021, 6, 20)
            assert result[1]["ratio"] == 0.5
            mock_ticker.assert_called_once_with("1306.T")

    def test_fetch_historical_splits_no_splits(self, service):
        """Test fetching when no splits exist."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = pd.Series([])  # Empty Series
            mock_ticker.return_value = mock_stock

            result = service.fetch_historical_splits("1306")

            assert result == []

    def test_fetch_historical_splits_error(self, service):
        """Test fetching with yfinance error."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("Network error")

            with pytest.raises(ValueError, match="Failed to fetch splits"):
                service.fetch_historical_splits("1306")

    def test_sync_splits_for_etf_new_splits(
        self, service, mock_splits_data, db_session
    ):
        """Test syncing splits for an ETF with new splits."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = mock_splits_data
            mock_ticker.return_value = mock_stock

            result = service.sync_splits_for_etf("1306")

            assert result["etf_code"] == "1306"
            assert result["fetched"] == 2
            assert result["registered"] == 2
            assert result["skipped"] == 0
            assert result["error"] is None

            # Verify splits were saved to database
            splits = db_session.query(StockSplit).filter_by(etf_code="1306").all()
            assert len(splits) == 2
            assert splits[0].is_applied is False  # Default state
            assert splits[0].ratio in [2.0, 0.5]

    def test_sync_splits_for_etf_skip_existing(
        self, service, mock_splits_data, db_session
    ):
        """Test syncing skips already registered splits."""
        # Pre-register one split
        existing_split = StockSplit(
            etf_code="1306",
            split_date=date(2020, 1, 15),
            ratio=2.0,
            is_applied=False,
        )
        db_session.add(existing_split)
        db_session.commit()

        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = mock_splits_data
            mock_ticker.return_value = mock_stock

            result = service.sync_splits_for_etf("1306")

            assert result["fetched"] == 2
            assert result["registered"] == 1  # Only one new split
            assert result["skipped"] == 1  # One existing split
            assert result["error"] is None

    def test_sync_splits_for_etf_no_splits(self, service, db_session):
        """Test syncing for ETF with no splits."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = pd.Series([])
            mock_ticker.return_value = mock_stock

            result = service.sync_splits_for_etf("1306")

            assert result["fetched"] == 0
            assert result["registered"] == 0
            assert result["skipped"] == 0
            assert result["error"] is None

    def test_sync_splits_for_etf_error(self, service, db_session):
        """Test syncing handles errors gracefully."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("API error")

            result = service.sync_splits_for_etf("1306")

            assert result["error"] is not None
            assert "API error" in result["error"]

    def test_sync_all_etfs_success(self, service, mock_splits_data, db_session):
        """Test syncing multiple ETFs successfully."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_stock = MagicMock()
            mock_stock.splits = mock_splits_data
            mock_ticker.return_value = mock_stock

            etf_codes = ["1306", "1321"]
            result = service.sync_all_etfs(etf_codes)

            assert result["total"] == 2
            assert result["success"] == 2
            assert result["failed"] == 0
            assert result["total_fetched"] == 4  # 2 splits x 2 ETFs
            assert result["total_registered"] == 4
            assert result["total_skipped"] == 0
            assert len(result["results"]) == 2

    def test_sync_all_etfs_partial_failure(self, service, mock_splits_data, db_session):
        """Test syncing with some failures."""
        call_count = [0]

        def mock_ticker_side_effect(ticker):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call succeeds
                mock_stock = MagicMock()
                mock_stock.splits = mock_splits_data
                return mock_stock
            else:
                # Second call fails
                raise Exception("Network error")

        with patch("yfinance.Ticker", side_effect=mock_ticker_side_effect):
            etf_codes = ["1306", "1321"]
            result = service.sync_all_etfs(etf_codes)

            assert result["total"] == 2
            assert result["success"] == 1
            assert result["failed"] == 1
            assert result["total_fetched"] == 2  # Only from successful ETF

    def test_sync_all_etfs_empty_list(self, service, db_session):
        """Test syncing with empty ETF list."""
        result = service.sync_all_etfs([])

        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0
        assert result["results"] == []
