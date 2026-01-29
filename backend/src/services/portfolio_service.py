"""Portfolio service for calculating user's holdings and P&L."""
from decimal import Decimal
from typing import Dict, List, Optional

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

        # Group trades by ETF code and store earliest trade date
        holdings_data: Dict[str, Dict] = {}

        for trade in trades:
            code = trade.etf_code
            if code not in holdings_data:
                holdings_data[code] = {
                    "buy_quantity": 0,
                    "buy_amount": Decimal("0"),
                    "sell_quantity": 0,
                    "sell_amount": Decimal("0"),
                    "earliest_trade_date": trade.trade_date,
                }
            else:
                # Track earliest trade date for split adjustment
                if trade.trade_date < holdings_data[code]["earliest_trade_date"]:
                    holdings_data[code]["earliest_trade_date"] = trade.trade_date

            if trade.trade_type == "buy":
                holdings_data[code]["buy_quantity"] += trade.quantity
                holdings_data[code]["buy_amount"] += trade.total_amount
            else:
                holdings_data[code]["sell_quantity"] += trade.quantity
                holdings_data[code]["sell_amount"] += trade.total_amount

        # Calculate holdings
        result = []
        for code, data in holdings_data.items():
            held_quantity = data["buy_quantity"] - data["sell_quantity"]

            if held_quantity <= 0:
                continue

            # Calculate split adjustment factor from earliest trade date
            adjustment_factor = self.split_adjustment_service.get_adjustment_factor(
                code, data["earliest_trade_date"]
            )

            # Calculate average cost (FIFO approximation using total avg)
            if data["buy_quantity"] > 0:
                avg_cost = float(data["buy_amount"] / data["buy_quantity"])
            else:
                avg_cost = 0

            # Apply split adjustment
            adjusted_avg_cost = avg_cost / adjustment_factor
            adjusted_quantity = held_quantity * adjustment_factor

            # Total cost remains the same (original investment amount)
            total_cost = avg_cost * held_quantity

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
