"""Integration tests for trade service cache invalidation."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.models.etf import ETF
from src.models.trade import Trade
from src.repositories.etf_repository import ETFRepository
from src.repositories.stock_split_repository import StockSplitRepository
from src.repositories.trade_repository import TradeRepository
from src.services.portfolio_service import PortfolioService
from src.services.trade_service import TradeService


@pytest.fixture
def setup_services():
    """Setup services with mocks."""
    mock_trade_repo = Mock(spec=TradeRepository)
    mock_etf_repo = Mock(spec=ETFRepository)

    # Setup ETF mock
    mock_etf_repo.get_by_code.return_value = ETF(
        code="1234",
        name="Test ETF",
        market_price=Decimal("2000"),
    )

    # Setup trade mock (initially no trades)
    mock_trade_repo.get_by_user_id.return_value = []
    mock_trade_repo.create.return_value = None
    mock_trade_repo.update.return_value = None
    mock_trade_repo.delete.return_value = None

    trade_service = TradeService(mock_trade_repo, mock_etf_repo)

    return trade_service, mock_trade_repo, mock_etf_repo


def test_create_trade_clears_cache(setup_services):
    """Test that creating a trade clears portfolio cache."""
    trade_service, mock_trade_repo, mock_etf_repo = setup_services

    # Prime cache
    PortfolioService._valuation_cache["1:1m"] = (datetime.now(), [])
    PortfolioService._valuation_cache["1:3m"] = (datetime.now(), [])
    assert len(PortfolioService._valuation_cache) == 2

    # Create trade
    trade_service.create_trade(
        user_id=1,
        etf_code="1234",
        trade_type="buy",
        quantity=100,
        price=1000.0,
        trade_date="2024-01-01",
    )

    # Verify cache was cleared for user 1
    assert "1:1m" not in PortfolioService._valuation_cache
    assert "1:3m" not in PortfolioService._valuation_cache


def test_update_trade_clears_cache(setup_services):
    """Test that updating a trade clears portfolio cache."""
    trade_service, mock_trade_repo, mock_etf_repo = setup_services

    # Setup mock trade
    mock_trade = Trade(
        id=1,
        user_id=1,
        etf_code="1234",
        trade_type="buy",
        quantity=100,
        price=Decimal("1000"),
        trade_date=date(2024, 1, 1),
    )
    mock_trade_repo.get_by_id.return_value = mock_trade

    # Prime cache
    PortfolioService._valuation_cache["1:1m"] = (datetime.now(), [])

    # Update trade
    trade_service.update_trade(
        user_id=1,
        trade_id=1,
        quantity=200,
    )

    # Verify cache was cleared
    assert "1:1m" not in PortfolioService._valuation_cache


def test_delete_trade_clears_cache(setup_services):
    """Test that deleting a trade clears portfolio cache."""
    trade_service, mock_trade_repo, mock_etf_repo = setup_services

    # Setup mock trade
    mock_trade = Trade(
        id=1,
        user_id=1,
        etf_code="1234",
        trade_type="buy",
        quantity=100,
        price=Decimal("1000"),
        trade_date=date(2024, 1, 1),
    )
    mock_trade_repo.get_by_id.return_value = mock_trade

    # Prime cache
    PortfolioService._valuation_cache["1:1m"] = (datetime.now(), [])

    # Delete trade
    trade_service.delete_trade(user_id=1, trade_id=1)

    # Verify cache was cleared
    assert "1:1m" not in PortfolioService._valuation_cache


def test_cache_isolation_between_users(setup_services):
    """Test that cache invalidation only affects the specific user."""
    trade_service, mock_trade_repo, mock_etf_repo = setup_services

    # Setup mock trade for user 1
    mock_trade = Trade(
        id=1,
        user_id=1,
        etf_code="1234",
        trade_type="buy",
        quantity=100,
        price=Decimal("1000"),
        trade_date=date(2024, 1, 1),
    )
    mock_trade_repo.get_by_id.return_value = mock_trade

    # Prime cache for both users
    PortfolioService._valuation_cache["1:1m"] = (datetime.now(), [])
    PortfolioService._valuation_cache["2:1m"] = (datetime.now(), [])

    # Update user 1's trade
    trade_service.update_trade(user_id=1, trade_id=1, quantity=200)

    # Verify only user 1's cache was cleared
    assert "1:1m" not in PortfolioService._valuation_cache
    assert "2:1m" in PortfolioService._valuation_cache
