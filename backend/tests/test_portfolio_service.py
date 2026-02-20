"""Tests for portfolio service with stock split adjustment."""
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.models.etf import ETF
from src.models.stock_split import StockSplit
from src.models.trade import Trade
from src.repositories.cash_flow_repository import CashFlowRepository
from src.repositories.etf_repository import ETFRepository
from src.repositories.stock_split_repository import StockSplitRepository
from src.repositories.trade_repository import TradeRepository
from src.services.portfolio_service import PortfolioService
from src.services.split_adjustment_service import SplitAdjustmentService


@pytest.fixture
def mock_etf_repository():
    """Mock ETF repository."""
    mock = Mock(spec=ETFRepository)
    default_etf = ETF(
        code="1234",
        name="Test ETF",
        market_price=Decimal("2000"),
    )
    mock.get_by_code.return_value = default_etf
    mock.get_by_codes.return_value = {"1234": default_etf}
    return mock


@pytest.fixture
def mock_trade_repository():
    """Mock trade repository."""
    return Mock(spec=TradeRepository)


@pytest.fixture
def mock_split_repository():
    """Mock stock split repository."""
    return Mock(spec=StockSplitRepository)


@pytest.fixture
def mock_cash_flow_repository():
    """Mock cash flow repository."""
    mock = Mock(spec=CashFlowRepository)
    mock.get_by_user_id.return_value = []
    return mock


def test_no_split_simple_buy(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
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
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
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
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
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
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 200.0  # 100 * 2
    assert holdings[0]["average_cost"] == 1000.0  # 2000 / 2
    assert holdings[0]["total_cost"] == 200000.0  # Original investment


def test_split_after_all_trades(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
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
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    # Execute
    holdings = service.get_holdings(1)

    # Verify
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 50.0  # No adjustment
    assert holdings[0]["average_cost"] == 1000.0
    assert holdings[0]["total_cost"] == 50000.0


def test_split_between_trades(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
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
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
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
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
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
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
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


# --- Total asset summary tests (cash flow method) ---


def test_summary_cash_flow_partial_sell(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """Pattern A: Partial sell - cash balance retains sell proceeds."""
    # Setup: Buy 100 at 2000 yen, sell 30 at 2500 yen
    # Current price: 2300 yen
    etf_2300 = ETF(code="1234", name="Test ETF", market_price=Decimal("2300"))
    mock_etf_repository.get_by_code.return_value = etf_2300
    mock_etf_repository.get_by_codes.return_value = {"1234": etf_2300}
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=30,
            price=Decimal("2500"),
            trade_date=date(2024, 6, 15),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    summary = service.get_portfolio_summary(1)

    # cash_balance: buy -> external funds (cash=0), sell 30*2500=75000 -> cash=75000
    assert summary["cash_balance"] == 75000.0
    # total_value: 70 shares * 2300 = 161000
    assert summary["total_value"] == 161000.0
    # total_asset = 161000 + 75000 = 236000
    assert summary["total_asset"] == 236000.0


def test_summary_cash_flow_no_sell(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """Pattern B: Buy only - cash balance is zero."""
    # Setup: Buy 50 at 1800 yen
    # Current price: 2000 yen
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=50,
            price=Decimal("1800"),
            trade_date=date(2024, 3, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    summary = service.get_portfolio_summary(1)

    # cash_balance: buy -> external funds (cash=0)
    assert summary["cash_balance"] == 0.0
    # total_value: 50 shares * 2000 = 100000
    assert summary["total_value"] == 100000.0
    # total_asset = total_value = 100000
    assert summary["total_asset"] == 100000.0


def test_summary_cash_flow_fully_sold(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """Pattern C: All shares sold - total asset equals cash balance."""
    # Setup: Buy 100 at 2000 yen, sell all 100 at 2500 yen
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=100,
            price=Decimal("2500"),
            trade_date=date(2024, 6, 15),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    summary = service.get_portfolio_summary(1)

    # cash_balance: buy -> external (cash=0), sell 100*2500=250000 -> cash=250000
    assert summary["cash_balance"] == 250000.0
    # total_value: 0 shares => 0
    assert summary["total_value"] == 0
    assert summary["holdings_count"] == 0
    # total_asset = 0 + 250000 = 250000
    assert summary["total_asset"] == 250000.0


def test_summary_cash_flow_reinvestment(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """Pattern D: Sell then reinvest - cash balance reduced by reinvestment."""
    # Setup: Buy 100 at 2000, sell 50 at 2500 (cash=125000),
    #        buy 30 at 2100 (cash=125000-63000=62000)
    # Current price: 2300 yen
    etf_2300 = ETF(code="1234", name="Test ETF", market_price=Decimal("2300"))
    mock_etf_repository.get_by_code.return_value = etf_2300
    mock_etf_repository.get_by_codes.return_value = {"1234": etf_2300}
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=50,
            price=Decimal("2500"),
            trade_date=date(2024, 6, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=30,
            price=Decimal("2100"),
            trade_date=date(2024, 9, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    summary = service.get_portfolio_summary(1)

    # cash flow: buy 200000 -> external (cash=0)
    #            sell 125000 -> cash=125000
    #            buy 63000 -> cash=125000-63000=62000
    assert summary["cash_balance"] == 62000.0
    # total_value: 80 shares * 2300 = 184000
    assert summary["total_value"] == 184000.0
    # total_asset = 184000 + 62000 = 246000
    assert summary["total_asset"] == 246000.0


# --- Valuation history tests (total asset = holdings + cash) ---


def test_calculate_value_at_date_buy_only(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """_calculate_value_at_date: buy only - cash_balance=0, returns holdings value."""
    trades = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
    ]
    mock_split_repository.get_approved_splits_between.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    target_date = date(2024, 3, 1)
    price_map = {target_date: {"1234": 2500.0}}

    result = service._calculate_value_at_date(trades, target_date, price_map)

    # holdings: 100 shares * 2500 = 250000, cash: 0
    assert result["total_asset"] == 250000.0
    # unrealized_pnl: 250000 - (2000 * 100) = 50000
    assert result["unrealized_pnl"] == 50000.0
    # cash_balance: buy -> external funds (cash=0)
    assert result["cash_balance"] == 0.0
    # total_cost: avg_cost 2000 * 100 = 200000
    assert result["total_cost"] == 200000.0


def test_calculate_value_at_date_partial_sell(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """_calculate_value_at_date: partial sell - cash_balance from sell proceeds."""
    trades = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=30,
            price=Decimal("2500"),
            trade_date=date(2024, 6, 15),
        ),
    ]
    mock_split_repository.get_approved_splits_between.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    target_date = date(2024, 8, 1)
    price_map = {target_date: {"1234": 2300.0}}

    result = service._calculate_value_at_date(trades, target_date, price_map)

    # holdings: 70 shares * 2300 = 161000
    # cash: sell 30*2500=75000, buy 200000 > cash so cash=0 before sell
    # cash flow: buy -> external (cash=0), sell 75000 -> cash=75000
    # total = 161000 + 75000 = 236000
    assert result["total_asset"] == 236000.0
    # unrealized_pnl: 161000 - (avg_cost 2000 * 70) = 161000 - 140000 = 21000
    assert result["unrealized_pnl"] == 21000.0
    # cash_balance: sell 75000
    assert result["cash_balance"] == 75000.0
    # total_cost: avg_cost 2000 * 70 = 140000
    assert result["total_cost"] == 140000.0


def test_calculate_value_at_date_reinvestment(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """_calculate_value_at_date: sell then reinvest - cash reduced by reinvestment."""
    trades = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=50,
            price=Decimal("2500"),
            trade_date=date(2024, 6, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=30,
            price=Decimal("2100"),
            trade_date=date(2024, 9, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_between.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    target_date = date(2024, 10, 1)
    price_map = {target_date: {"1234": 2300.0}}

    result = service._calculate_value_at_date(trades, target_date, price_map)

    # holdings: (100 - 50 + 30) = 80 shares * 2300 = 184000
    # cash flow: buy 200000 -> external (cash=0)
    #            sell 125000 -> cash=125000
    #            buy 63000 -> cash=125000-63000=62000
    # total = 184000 + 62000 = 246000
    assert result["total_asset"] == 246000.0
    # unrealized_pnl: 184000 - (avg_cost * 80)
    # avg_cost = (200000 + 63000) / (100 + 30) = 263000 / 130 = 2023.076923...
    # total_cost = 2023.076923... * 80 = 161846.153846...
    # unrealized_pnl = 184000 - 161846.153846... = 22153.85 (rounded)
    assert result["unrealized_pnl"] == 22153.85
    # cash_balance: 125000 - 63000 = 62000
    assert result["cash_balance"] == 62000.0
    # total_cost: 2023.076923... * 80 = 161846.15 (rounded)
    assert result["total_cost"] == 161846.15


def test_summary_cash_flow_same_day_trades(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """Pattern E: Same-day sell and buy - sells processed before buys."""
    # Setup: Buy 100 at 2000 (2024-01-15),
    #        sell 50 at 2500 (2024-06-15, same day),
    #        buy 20 at 2400 (2024-06-15, same day)
    # Current price: 2300 yen
    etf_2300 = ETF(code="1234", name="Test ETF", market_price=Decimal("2300"))
    mock_etf_repository.get_by_code.return_value = etf_2300
    mock_etf_repository.get_by_codes.return_value = {"1234": etf_2300}
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("2000"),
            trade_date=date(2024, 1, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=50,
            price=Decimal("2500"),
            trade_date=date(2024, 6, 15),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=20,
            price=Decimal("2400"),
            trade_date=date(2024, 6, 15),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    summary = service.get_portfolio_summary(1)

    # cash flow (sorted: sell before buy on same day):
    #   buy 200000 (2024-01-15) -> external (cash=0)
    #   sell 125000 (2024-06-15) -> cash=125000
    #   buy 48000  (2024-06-15) -> cash=125000-48000=77000
    assert summary["cash_balance"] == 77000.0
    # total_value: 70 shares * 2300 = 161000
    assert summary["total_value"] == 161000.0
    # total_asset = 161000 + 77000 = 238000
    assert summary["total_asset"] == 238000.0


# --- Total P&L tests ---


def test_total_pnl_buy_only(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """total_pnl for buy-only holding: current_value - buy_amount."""
    # Setup: Buy 100 shares at 1000 yen, current price 2000 yen
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
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    holdings = service.get_holdings(1)

    assert len(holdings) == 1
    # current_value = 100 * 2000 = 200000
    # total_pnl = current_value - buy_amount = 200000 - 100000 = 100000
    assert holdings[0]["total_pnl"] == 100000.0
    assert holdings[0]["total_buy_amount"] == 100000.0
    assert holdings[0]["total_sell_amount"] == 0.0
    # total_pnl_percent = 100000 / 100000 * 100 = 100.0
    assert holdings[0]["total_pnl_percent"] == 100.0


def test_total_pnl_partial_sell(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """total_pnl for partial sell: current_value + sell_amount - buy_amount."""
    # Setup: Buy 100 at 1000, sell 30 at 1500, current price 2000
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("1000"),
            trade_date=date(2024, 1, 1),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=30,
            price=Decimal("1500"),
            trade_date=date(2024, 6, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    holdings = service.get_holdings(1)

    assert len(holdings) == 1
    # current_value = 70 * 2000 = 140000
    # sell_amount = 30 * 1500 = 45000
    # buy_amount = 100 * 1000 = 100000
    # total_pnl = 140000 + 45000 - 100000 = 85000
    assert holdings[0]["total_pnl"] == 85000.0
    assert holdings[0]["total_buy_amount"] == 100000.0
    assert holdings[0]["total_sell_amount"] == 45000.0
    # total_pnl_percent = 85000 / 100000 * 100 = 85.0
    assert holdings[0]["total_pnl_percent"] == 85.0


def test_total_pnl_full_sell(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """total_pnl for fully sold holding: sell_amount - buy_amount (current_value=0)."""
    # Setup: Buy 100 at 1000, sell all 100 at 1500, current price 2000
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("1000"),
            trade_date=date(2024, 1, 1),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=100,
            price=Decimal("1500"),
            trade_date=date(2024, 6, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    # Must use include_sold=True to see fully sold holdings
    holdings = service.get_holdings(1, include_sold=True)

    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 0.0
    assert holdings[0]["current_value"] == 0
    # total_pnl = 0 + 150000 - 100000 = 50000
    assert holdings[0]["total_pnl"] == 50000.0
    assert holdings[0]["total_buy_amount"] == 100000.0
    assert holdings[0]["total_sell_amount"] == 150000.0
    # total_pnl_percent = 50000 / 100000 * 100 = 50.0
    assert holdings[0]["total_pnl_percent"] == 50.0


def test_include_sold_true(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """include_sold=True returns fully sold holdings."""
    # Setup: ETF "1234" fully sold, ETF "5678" still held
    etf_5678 = ETF(code="5678", name="Another ETF", market_price=Decimal("3000"))
    mock_etf_repository.get_by_codes.return_value = {
        "1234": ETF(code="1234", name="Test ETF", market_price=Decimal("2000")),
        "5678": etf_5678,
    }
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("1000"),
            trade_date=date(2024, 1, 1),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=100,
            price=Decimal("1500"),
            trade_date=date(2024, 6, 1),
        ),
        Trade(
            user_id=1,
            etf_code="5678",
            trade_type="buy",
            quantity=50,
            price=Decimal("2500"),
            trade_date=date(2024, 3, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    holdings = service.get_holdings(1, include_sold=True)

    # Both holdings returned: active first, then sold
    assert len(holdings) == 2
    codes = [h["etf_code"] for h in holdings]
    assert "1234" in codes
    assert "5678" in codes
    # Active holding (5678) should come first
    assert holdings[0]["etf_code"] == "5678"
    assert holdings[0]["quantity"] == 50.0
    assert holdings[0]["total_buy_amount"] == 125000.0
    assert holdings[0]["total_sell_amount"] == 0.0
    # total_pnl = 150000 + 0 - 125000 = 25000
    # total_pnl_percent = 25000 / 125000 * 100 = 20.0
    assert holdings[0]["total_pnl_percent"] == 20.0
    # Sold holding (1234) should come second
    assert holdings[1]["etf_code"] == "1234"
    assert holdings[1]["quantity"] == 0.0
    assert holdings[1]["total_buy_amount"] == 100000.0
    assert holdings[1]["total_sell_amount"] == 150000.0
    # total_pnl_percent = 50000 / 100000 * 100 = 50.0
    assert holdings[1]["total_pnl_percent"] == 50.0


def test_include_sold_false_default(
    mock_trade_repository, mock_etf_repository, mock_split_repository,
    mock_cash_flow_repository,
):
    """include_sold=False (default) excludes fully sold holdings."""
    # Same setup as above: ETF "1234" fully sold, ETF "5678" still held
    etf_5678 = ETF(code="5678", name="Another ETF", market_price=Decimal("3000"))
    mock_etf_repository.get_by_codes.return_value = {
        "1234": ETF(code="1234", name="Test ETF", market_price=Decimal("2000")),
        "5678": etf_5678,
    }
    mock_trade_repository.get_by_user_id.return_value = [
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="buy",
            quantity=100,
            price=Decimal("1000"),
            trade_date=date(2024, 1, 1),
        ),
        Trade(
            user_id=1,
            etf_code="1234",
            trade_type="sell",
            quantity=100,
            price=Decimal("1500"),
            trade_date=date(2024, 6, 1),
        ),
        Trade(
            user_id=1,
            etf_code="5678",
            trade_type="buy",
            quantity=50,
            price=Decimal("2500"),
            trade_date=date(2024, 3, 1),
        ),
    ]
    mock_split_repository.get_approved_splits_since.return_value = []

    split_service = SplitAdjustmentService(mock_split_repository)
    service = PortfolioService(
        mock_trade_repository, mock_etf_repository, split_service,
        mock_cash_flow_repository,
    )

    # Default (include_sold=False)
    holdings = service.get_holdings(1)

    # Only active holding returned
    assert len(holdings) == 1
    assert holdings[0]["etf_code"] == "5678"
    assert holdings[0]["quantity"] == 50.0
    assert holdings[0]["total_buy_amount"] == 125000.0
    assert holdings[0]["total_sell_amount"] == 0.0
    # total_pnl_percent = 25000 / 125000 * 100 = 20.0
    assert holdings[0]["total_pnl_percent"] == 20.0
