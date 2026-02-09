"""Portfolio service for calculating user's holdings and P&L."""
import logging
import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.config.settings import Config
from src.models import PriceHistory
from src.repositories.etf_repository import ETFRepository
from src.repositories.trade_repository import TradeRepository
from src.services.split_adjustment_service import SplitAdjustmentService

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for portfolio calculations."""

    # クラスレベルキャッシュ: {user_id}:{period} -> (timestamp, data)
    _valuation_cache: Dict[str, Tuple[datetime, List[Dict]]] = {}
    _cache_ttl = Config.CACHE_TTL  # 環境変数CACHE_TTLで設定可能（デフォルト: 300秒）

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

    @classmethod
    def clear_valuation_cache(cls, user_id: Optional[int] = None) -> None:
        """
        Clear valuation cache.

        Args:
            user_id: If specified, clear only this user's cache. Otherwise, clear all.
        """
        if user_id is None:
            cls._valuation_cache.clear()
            logger.info("Cleared all valuation cache")
        else:
            keys_to_remove = [
                k for k in cls._valuation_cache if k.startswith(f"{user_id}:")
            ]
            for key in keys_to_remove:
                del cls._valuation_cache[key]
            logger.info(f"Cleared valuation cache for user_id={user_id}")

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
        - holding_days (保有日数)
        - holding_period (保有期間テキスト)
        - annualized_return (年率リターン)
        - annualized_pnl (年率評価損益)
        """
        trades = self.trade_repository.get_by_user_id(user_id)

        # Group trades by ETF code and accumulate adjusted quantities
        holdings_data: Dict[str, Dict] = {}
        trades_by_code: Dict[str, List] = {}

        for trade in trades:
            code = trade.etf_code
            if code not in holdings_data:
                holdings_data[code] = {
                    "adjusted_buy_quantity": 0.0,
                    "adjusted_sell_quantity": 0.0,
                    "original_buy_amount": Decimal("0"),
                }
                trades_by_code[code] = []

            trades_by_code[code].append(trade)

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

            # Calculate holding period and annualized metrics
            holding_days = self._calculate_holding_days(trades_by_code[code], code)
            holding_period = self._format_holding_period(holding_days)

            # Calculate annualized return (CAGR) and annualized P&L
            annualized_return = None
            annualized_pnl = None
            if holding_days > 0 and total_cost > 0:
                years = holding_days / 365.0
                if years >= 0.01:  # At least ~4 days
                    # CAGR: ((current_value / total_cost) ^ (1/years) - 1) * 100
                    ratio = current_value / total_cost
                    if ratio > 0:
                        annualized_return = round(
                            (math.pow(ratio, 1.0 / years) - 1) * 100, 2
                        )
                    # Annualized P&L: unrealized_pnl / years
                    annualized_pnl = round(unrealized_pnl / years, 2)

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
                    "holding_days": holding_days,
                    "holding_period": holding_period,
                    "annualized_return": annualized_return,
                    "annualized_pnl": annualized_pnl,
                }
            )

        # Sort by current_value descending
        result.sort(key=lambda x: x["current_value"], reverse=True)
        return result

    def _calculate_holding_days(self, trades_for_code: List, code: str) -> int:
        """
        Calculate total holding days for a specific ETF code.

        Only counts days when quantity > 0.
        If position was fully sold and later re-acquired,
        the gap period is not counted.
        """
        if not trades_for_code:
            return 0

        # Sort trades by trade_date ascending
        sorted_trades = sorted(trades_for_code, key=lambda t: t.trade_date)

        total_holding_days = 0
        running_qty = 0.0
        holding_start: Optional[date] = None

        for trade in sorted_trades:
            # Calculate split adjustment factor from this trade's date to now
            adjustment_factor = self.split_adjustment_service.get_adjustment_factor(
                code, trade.trade_date
            )
            adjusted_qty = trade.quantity * adjustment_factor

            if trade.trade_type == "buy":
                if running_qty <= 0:
                    # Start new holding period
                    holding_start = trade.trade_date
                running_qty += adjusted_qty
            else:  # sell
                running_qty -= adjusted_qty
                if running_qty <= 0 and holding_start:
                    # Position closed, count days
                    total_holding_days += (trade.trade_date - holding_start).days
                    holding_start = None
                    running_qty = 0.0

        # If still holding, add days until today
        if running_qty > 0 and holding_start:
            total_holding_days += (date.today() - holding_start).days

        return total_holding_days

    def _format_holding_period(self, days: int) -> str:
        """
        Format holding days into human-readable text like "1年2ヶ月".
        """
        if days <= 0:
            return "0日"

        years = days // 365
        remaining_days = days % 365
        months = remaining_days // 30

        parts = []
        if years > 0:
            parts.append(f"{years}年")
        if months > 0:
            parts.append(f"{months}ヶ月")
        if not parts:
            parts.append(f"{days}日")

        return "".join(parts)

    def get_portfolio_summary(self, user_id: int) -> Dict:
        """
        Get portfolio summary statistics.

        Returns:
        - total_value: Sum of all current values
        - total_cost: Sum of all costs
        - total_unrealized_pnl: Sum of all unrealized P&L
        - total_unrealized_pnl_percent: Overall P&L percentage
        - holdings_count: Number of unique ETFs held
        - cash_balance: Cash balance from chronological trade processing
        - total_asset: total_value + cash_balance
        """
        holdings = self.get_holdings(user_id)

        total_value = sum(h["current_value"] for h in holdings)
        total_cost = sum(h["total_cost"] for h in holdings)
        unrealized_pnl = sum(h["unrealized_pnl"] for h in holdings)
        pnl_percent = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0

        # Calculate cash balance using chronological cash flow
        trades = self.trade_repository.get_by_user_id(user_id)
        # Sort: trade_date ascending, same day sells before buys
        trades_sorted = sorted(
            trades,
            key=lambda t: (t.trade_date, 0 if t.trade_type == "sell" else 1),
        )
        cash_balance = 0.0
        for trade in trades_sorted:
            if trade.trade_type == "sell":
                cash_balance += float(trade.total_amount)
            else:
                buy_amount = float(trade.total_amount)
                if cash_balance >= buy_amount:
                    cash_balance -= buy_amount
                else:
                    cash_balance = 0.0  # shortfall covered by external funds

        total_asset = total_value + cash_balance

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_unrealized_pnl": round(unrealized_pnl, 2),
            "total_unrealized_pnl_percent": round(pnl_percent, 2),
            "holdings_count": len(holdings),
            "cash_balance": round(cash_balance, 2),
            "total_asset": round(total_asset, 2),
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
        # キャッシュチェック
        cache_key = f"{user_id}:{period}"
        if cache_key in self._valuation_cache:
            cached_time, cached_data = self._valuation_cache[cache_key]
            age = (datetime.now() - cached_time).total_seconds()
            if age < self._cache_ttl:
                logger.info(
                    f"Valuation history cache hit: user_id={user_id}, period={period}, age={age:.1f}s"
                )
                return cached_data

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
            # 取引0件も空配列としてキャッシュ
            self._valuation_cache[cache_key] = (datetime.now(), [])
            return []

        # Collect ETF codes from trades
        etf_codes = list(set(t.etf_code for t in trades))

        # Get price histories for all ETF codes in period
        price_map = self._build_price_map(etf_codes, start_date)
        if not price_map:
            # 価格データなし時も空配列としてキャッシュ
            self._valuation_cache[cache_key] = (datetime.now(), [])
            return []

        # Generate valuation for each date
        all_dates = sorted(price_map.keys())
        result = []

        for target_date in all_dates:
            total_asset = self._calculate_value_at_date(trades, target_date, price_map)
            if total_asset > 0:
                result.append(
                    {
                        "date": target_date.strftime("%Y-%m-%d"),
                        "value": round(total_asset, 2),
                    }
                )

        # キャッシュに保存
        self._valuation_cache[cache_key] = (datetime.now(), result)
        logger.info(f"Valuation history cached: user_id={user_id}, period={period}")

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
        """Calculate total asset value (holdings + cash) at a specific date."""
        # Filter trades up to target_date and calculate holdings
        holdings: Dict[str, float] = {}
        trades_up_to_date = []

        for trade in trades:
            if trade.trade_date > target_date:
                continue

            trades_up_to_date.append(trade)

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

        # Calculate cash balance from trades up to target_date
        trades_sorted = sorted(
            trades_up_to_date,
            key=lambda t: (t.trade_date, 0 if t.trade_type == "sell" else 1),
        )
        cash_balance = 0.0
        for trade in trades_sorted:
            if trade.trade_type == "sell":
                cash_balance += float(trade.total_amount)
            else:
                buy_amount = float(trade.total_amount)
                if cash_balance >= buy_amount:
                    cash_balance -= buy_amount
                else:
                    cash_balance = 0.0

        # Calculate holdings value using prices at target_date
        prices = price_map.get(target_date, {})
        holdings_value = 0.0

        for code, qty in holdings.items():
            if qty > 0 and code in prices:
                holdings_value += qty * prices[code]

        return holdings_value + cash_balance
