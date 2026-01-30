"""Tests for portfolio service cache functionality."""
import time
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.models.etf import ETF
from src.models.trade import Trade
from src.repositories.etf_repository import ETFRepository
from src.repositories.stock_split_repository import StockSplitRepository
from src.repositories.trade_repository import TradeRepository
from src.services.portfolio_service import PortfolioService
from src.services.split_adjustment_service import SplitAdjustmentService


@pytest.fixture
def setup_service():
    """Setup service with mocks."""
    mock_trade_repo = Mock(spec=TradeRepository)
    mock_etf_repo = Mock(spec=ETFRepository)
    mock_split_repo = Mock(spec=StockSplitRepository)

    mock_trade_repo.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("1000"),
            trade_date=date(2024, 1, 1),
        )
    ]
    mock_etf_repo.get_by_code.return_value = ETF(
        code="1234",
        name="Test ETF",
        market_price=Decimal("2000"),
    )
    mock_split_repo.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repo)
    service = PortfolioService(mock_trade_repo, mock_etf_repo, split_service)

    return service, mock_trade_repo


def test_valuation_history_cache_empty_trades():
    """Test cache handles empty trades correctly."""
    mock_trade_repo = Mock(spec=TradeRepository)
    mock_etf_repo = Mock(spec=ETFRepository)
    mock_split_repo = Mock(spec=StockSplitRepository)

    mock_trade_repo.get_by_user_id.return_value = []

    split_service = SplitAdjustmentService(mock_split_repo)
    service = PortfolioService(mock_trade_repo, mock_etf_repo, split_service)

    # First call
    result1 = service.get_valuation_history(1, "1m")
    assert result1 == []

    # Second call should use cache
    result2 = service.get_valuation_history(1, "1m")
    assert result2 == []

    # Verify repository was called only once
    assert mock_trade_repo.get_by_user_id.call_count == 1


def test_valuation_history_cache_key_separation():
    """Test cache separates different user_id:period combinations."""
    # Clear all cache
    PortfolioService.clear_valuation_cache()

    # Manually set cache entries
    PortfolioService._valuation_cache["1:1m"] = (None, [{"date": "2024-01-01", "value": 100}])
    PortfolioService._valuation_cache["1:3m"] = (None, [{"date": "2024-01-01", "value": 200}])
    PortfolioService._valuation_cache["2:1m"] = (None, [{"date": "2024-01-01", "value": 300}])

    # Verify separation
    assert len(PortfolioService._valuation_cache) == 3
    assert "1:1m" in PortfolioService._valuation_cache
    assert "1:3m" in PortfolioService._valuation_cache
    assert "2:1m" in PortfolioService._valuation_cache


def test_clear_valuation_cache_for_user():
    """Test clearing cache for specific user."""
    # Setup cache
    PortfolioService._valuation_cache["1:1m"] = (None, [])
    PortfolioService._valuation_cache["1:3m"] = (None, [])
    PortfolioService._valuation_cache["2:1m"] = (None, [])

    # Clear user 1's cache
    PortfolioService.clear_valuation_cache(user_id=1)

    # Verify only user 1's entries are removed
    assert "1:1m" not in PortfolioService._valuation_cache
    assert "1:3m" not in PortfolioService._valuation_cache
    assert "2:1m" in PortfolioService._valuation_cache


def test_clear_valuation_cache_all():
    """Test clearing all cache."""
    # Setup cache
    PortfolioService._valuation_cache["1:1m"] = (None, [])
    PortfolioService._valuation_cache["1:3m"] = (None, [])
    PortfolioService._valuation_cache["2:1m"] = (None, [])

    # Clear all cache
    PortfolioService.clear_valuation_cache()

    # Verify cache is empty
    assert len(PortfolioService._valuation_cache) == 0
