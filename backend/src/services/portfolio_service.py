"""Portfolio service for calculating user's holdings and P&L."""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from src.models import PriceHistory
from src.repositories.etf_repository import ETFRepository
from src.repositories.trade_repository import TradeRepository
from src.services.split_adjustment_service import SplitAdjustmentService


class PortfolioService:
    """Service for portfolio calculations."""

    def __init__(
        self,
        trade_repository: Optional[TradeRepository] = None,
        etf_repository: Optional[ETFRepository] = None,
        split_adjustment_service: Optional[SplitAdjustmentService] = None,
    ):
        """Initialize portfolio service."""
        self.trade_repository = trade_repository or TradeRepository()
        self.etf_repository = etf_repository or ETFRepository()
        self.split_adjustment_service = (
            split_adjustment_service or SplitAdjustmentService()
        )

    def get_holdings(self, user_id: int) -> List[Dict]:
        """
        Calculate current holdings from trade history.

        Returns list of holdings with:
        - etf_code, etf info
        - quantity (held)
        - average_cost (avg purchase price)
        - total_cost (total investment)
        - current_price
        - current_value
        - unrealized_pnl
        - unrealized_pnl_percent
        """
        trades = self.trade_repository.get_by_user_id(user_id)

        # Group trades by ETF code and accumulate adjusted quantities
        holdings_data: Dict[str, Dict] = {}

        for trade in trades:
            code = trade.etf_code
            if code not in holdings_data:
                holdings_data[code] = {
                    "adjusted_buy_quantity": 0.0,
                    "adjusted_sell_quantity": 0.0,
                    "original_buy_amount": Decimal("0"),
                }

            # Calculate split adjustment factor from this trade's date to now
            adjustment_factor = self.split_adjustment_service.get_adjustment_factor(
                code, trade.trade_date
            )

            # Apply adjustment to this trade's quantity
            adjusted_quantity = trade.quantity * adjustment_factor

            if trade.trade_type == "buy":
                holdings_data[code]["adjusted_buy_quantity"] += adjusted_quantity
                holdings_data[code]["original_buy_amount"] += trade.total_amount
            else:
                holdings_data[code]["adjusted_sell_quantity"] += adjusted_quantity

        # Calculate holdings
        result = []
        for code, data in holdings_data.items():
            adjusted_quantity = (
                data["adjusted_buy_quantity"] - data["adjusted_sell_quantity"]
            )

            if adjusted_quantity <= 0:
                continue

            # Calculate average cost based on adjusted quantity
            if data["adjusted_buy_quantity"] > 0:
                adjusted_avg_cost = (
                    float(data["original_buy_amount"]) / data["adjusted_buy_quantity"]
                )
            else:
                adjusted_avg_cost = 0

            # Total cost is the cost of currently held shares (excludes sold shares)
            total_cost = adjusted_avg_cost * adjusted_quantity

            # Get ETF info and current price
            etf = self.etf_repository.get_by_code(code)
            current_price = float(etf.market_price) if etf and etf.market_price else 0.0
            current_value = current_price * adjusted_quantity

            unrealized_pnl = current_value - float(total_cost)
            pnl_percent = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0

            result.append(
                {
                    "etf_code": code,
                    "etf": etf.to_dict() if etf else None,
                    "quantity": adjusted_quantity,
                    "average_cost": round(adjusted_avg_cost, 2),
                    "total_cost": round(total_cost, 2),
                    "current_price": current_price,
                    "current_value": round(current_value, 2),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_percent": round(pnl_percent, 2),
                }
            )

        # Sort by current_value descending
        result.sort(key=lambda x: x["current_value"], reverse=True)
        return result

    def get_portfolio_summary(self, user_id: int) -> Dict:
        """
        Get portfolio summary statistics.

        Returns:
        - total_value: Sum of all current values
        - total_cost: Sum of all costs
        - total_unrealized_pnl: Sum of all unrealized P&L
        - total_unrealized_pnl_percent: Overall P&L percentage
        - holdings_count: Number of unique ETFs held
        """
        holdings = self.get_holdings(user_id)

        total_value = sum(h["current_value"] for h in holdings)
        total_cost = sum(h["total_cost"] for h in holdings)
        total_pnl = sum(h["unrealized_pnl"] for h in holdings)
        pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_unrealized_pnl": round(total_pnl, 2),
            "total_unrealized_pnl_percent": round(pnl_percent, 2),
            "holdings_count": len(holdings),
        }

    def get_valuation_history(self, user_id: int, period: str = "1y") -> List[Dict]:
        """
        Calculate portfolio valuation history over a period.

        Args:
            user_id: User ID
            period: Time period ('1m', '3m', '6m', '1y')

        Returns:
            List of {date, value} representing daily portfolio value
        """
        period_days = {
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "1y": 365,
            "3y": 1095,
            "5y": 1825,
            "10y": 3650,
            "20y": 7300,
        }
        days = period_days.get(period, 30)
        start_date = date.today() - timedelta(days=days)

        # Get all trades before end of period
        trades = self.trade_repository.get_by_user_id(user_id)
        if not trades:
            return []

        # Collect ETF codes from trades
        etf_codes = list(set(t.etf_code for t in trades))

        # Get price histories for all ETF codes in period
        price_map = self._build_price_map(etf_codes, start_date)
        if not price_map:
            return []

        # Generate valuation for each date
        all_dates = sorted(price_map.keys())
        result = []

        for target_date in all_dates:
            total_value = self._calculate_value_at_date(trades, target_date, price_map)
            if total_value > 0:
                result.append(
                    {
                        "date": target_date.strftime("%Y-%m-%d"),
                        "value": round(total_value, 2),
                    }
                )

        return result

    def _build_price_map(
        self, etf_codes: List[str], start_date: date
    ) -> Dict[date, Dict[str, float]]:
        """
        Build a map of date -> {etf_code -> close_price}.

        Applies forward-fill for missing dates.
        """
        # Query price histories for all codes
        records = (
            PriceHistory.query.filter(
                PriceHistory.etf_code.in_(etf_codes),
                PriceHistory.date >= start_date,
            )
            .order_by(PriceHistory.date)
            .all()
        )

        # Build raw price map
        raw_map: Dict[date, Dict[str, float]] = {}
        for r in records:
            if r.date not in raw_map:
                raw_map[r.date] = {}
            raw_map[r.date][r.etf_code] = r.close

        if not raw_map:
            return {}

        # Forward-fill missing prices
        all_dates = sorted(raw_map.keys())
        filled_map: Dict[date, Dict[str, float]] = {}
        last_prices: Dict[str, float] = {}

        for d in all_dates:
            # Update last known prices with today's data
            for code, price in raw_map[d].items():
                last_prices[code] = price
            # Copy all last known prices to this date
            filled_map[d] = last_prices.copy()

        return filled_map

    def _calculate_value_at_date(
        self,
        trades: List,
        target_date: date,
        price_map: Dict[date, Dict[str, float]],
    ) -> float:
        """Calculate total portfolio value at a specific date."""
        # Calculate holdings at target_date
        holdings: Dict[str, float] = {}

        for trade in trades:
            if trade.trade_date > target_date:
                continue

            code = trade.etf_code
            # Get adjustment factor from trade date to target date
            adjustment = self.split_adjustment_service.get_adjustment_factor_at_date(
                code, trade.trade_date, target_date
            )

            adjusted_qty = trade.quantity * adjustment

            if code not in holdings:
                holdings[code] = 0.0

            if trade.trade_type == "buy":
                holdings[code] += adjusted_qty
            else:
                holdings[code] -= adjusted_qty

        # Calculate value using prices at target_date
        prices = price_map.get(target_date, {})
        total_value = 0.0

        for code, qty in holdings.items():
            if qty > 0 and code in prices:
                total_value += qty * prices[code]

        return total_value
