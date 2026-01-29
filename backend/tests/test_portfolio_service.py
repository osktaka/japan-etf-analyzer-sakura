"""Tests for portfolio service with stock split adjustment."""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.models.etf import ETF
from src.models.stock_split import StockSplit
from src.models.trade import Trade
from src.repositories.etf_repository import ETFRepository
from src.repositories.stock_split_repository import StockSplitRepository
from src.repositories.trade_repository import TradeRepository
from src.services.portfolio_service import PortfolioService
from src.services.split_adjustment_service import SplitAdjustmentService


@pytest.fixture
def mock_etf_repository():
    """Mock ETF repository."""
    mock = Mock(spec=ETFRepository)
    mock.get_by_code.return_value = ETF(
        code="1234",
        name="Test ETF",
        market_price=Decimal("2000"),
    )
    return mock


@pytest.fixture
def mock_trade_repository():
    """Mock trade repository."""
    return Mock(spec=TradeRepository)


@pytest.fixture
def mock_split_repository():
    """Mock stock split repository."""
    return Mock(spec=StockSplitRepository)


def test_no_split_simple_buy(
    mock_trade_repository, mock_etf_repository, mock_split_repository
):
    """Test portfolio calculation with no splits."""
    # Setup: Buy 100 shares at 1000 yen
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("1000"),
            trade_date=date(2024, 1, 1),
        )
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    assert holdings[0]["etf_code"] == "1234"
    assert holdings[0]["quantity"] == 100.0
    assert holdings[0]["average_cost"] == 1000.0
    assert holdings[0]["total_cost"] == 100000.0


def test_split_before_all_trades(
    mock_trade_repository, mock_etf_repository, mock_split_repository
):
    """Test: All purchases before 2:1 split."""
    # Setup: Buy 100 shares at 2000 yen, then 2:1 split
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 1),
        )
    ]
    mock_split_repository.get_approved_splits_since.return_value = [
        StockSplit(
            etf_code="1234",
            split_date=date(2024, 2, 1),
            ratio=2.0,
            is_applied=True,
        )
    ]

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 200.0  # 100 * 2
    assert holdings[0]["average_cost"] == 1000.0  # 2000 / 2
    assert holdings[0]["total_cost"] == 200000.0  # Original investment


def test_split_after_all_trades(
    mock_trade_repository, mock_etf_repository, mock_split_repository
):
    """Test: All purchases after 2:1 split."""
    # Setup: 2:1 split on Feb 1, then buy 50 shares at 1000 yen
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=50,
            price=Decimal("1000"),
            trade_date=date(2024, 3, 1),
        )
    ]
    # No splits after Mar 1
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 50.0  # No adjustment
    assert holdings[0]["average_cost"] == 1000.0
    assert holdings[0]["total_cost"] == 50000.0


def test_split_between_trades(
    mock_trade_repository, mock_etf_repository, mock_split_repository
):
    """Test: Purchase before and after 2:1 split (key test case)."""
    # Setup: Buy 100 at 2000 yen on Jan 1, 2:1 split on Feb 1, buy 50 at 1000 yen on Mar 1
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 1),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=50,
            price=Decimal("1000"),
            trade_date=date(2024, 3, 1),
        ),
    ]

    def get_splits_side_effect(etf_code, trade_date):
        if trade_date == date(2024, 1, 1):
            # Jan 1 trade: split on Feb 1 applies
            return [
                StockSplit(
                    etf_code="1234",
                    split_date=date(2024, 2, 1),
                    ratio=2.0,
                    is_applied=True,
                )
            ]
        else:
            # Mar 1 trade: no splits after
            return []

    mock_split_repository.get_approved_splits_since.side_effect = (
        get_splits_side_effect
    )

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    # Adjusted quantity: (100 * 2) + (50 * 1) = 250
    assert holdings[0]["quantity"] == 250.0
    # Average cost: 250000 / 250 = 1000
    assert holdings[0]["average_cost"] == 1000.0
    # Total investment: 200000 + 50000 = 250000
    assert holdings[0]["total_cost"] == 250000.0


def test_split_with_sell(
    mock_trade_repository, mock_etf_repository, mock_split_repository
):
    """Test: Buy before split, sell after split."""
    # Setup: Buy 100 at 2000 yen on Jan 1, 2:1 split on Feb 1, sell 50 at 1000 yen on Mar 1
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 1),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=50,
            price=Decimal("1000"),
            trade_date=date(2024, 3, 1),
        ),
    ]

    def get_splits_side_effect(etf_code, trade_date):
        if trade_date == date(2024, 1, 1):
            return [
                StockSplit(
                    etf_code="1234",
                    split_date=date(2024, 2, 1),
                    ratio=2.0,
                    is_applied=True,
                )
            ]
        else:
            return []

    mock_split_repository.get_approved_splits_since.side_effect = (
        get_splits_side_effect
    )

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    # Adjusted quantity: (100 * 2) - (50 * 1) = 150
    assert holdings[0]["quantity"] == 150.0
    # Average cost: 200000 / 200 = 1000
    assert holdings[0]["average_cost"] == 1000.0
    # Total cost: 1000 * 150 = 150000 (excludes sold shares)
    assert holdings[0]["total_cost"] == 150000.0
