"""Trade service for managing user's ETF transactions."""
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Union

from src.models import Trade
from src.repositories.etf_repository import ETFRepository
from src.repositories.trade_repository import TradeRepository


class TradeService:
    """Service for trade operations."""

    def __init__(
        self,
        trade_repository: Optional[TradeRepository] = None,
        etf_repository: Optional[ETFRepository] = None,
    ):
        """Initialize trade service."""
        self.trade_repository = trade_repository or TradeRepository()
        self.etf_repository = etf_repository or ETFRepository()

    def _clear_portfolio_cache(self, user_id: int) -> None:
        """Clear portfolio-related cache after trade CUD operations."""
        # Avoid circular import by lazy import
        from src.services.portfolio_service import PortfolioService

        PortfolioService.clear_valuation_cache(user_id)

    def get_user_trades(
        self,
        user_id: int,
        start_date: Optional[Union[date, str]] = None,
        end_date: Optional[Union[date, str]] = None,
        search: Optional[str] = None,
    ) -> List[Dict]:
        """Get all trades for a user with ETF details.

        Args:
            user_id: User ID
            start_date: Filter trades on or after this date (date or YYYY-MM-DD string)
            end_date: Filter trades on or before this date (date or YYYY-MM-DD string)
            search: Search ETF code or name (partial match)

        Returns:
            List of trade dicts with ETF details
        """
        # 日付文字列をdateオブジェクトに変換
        parsed_start = self._parse_date(start_date) if start_date else None
        parsed_end = self._parse_date(end_date) if end_date else None

        # いずれかのフィルターがあればフィルター検索、なければ全件取得
        if parsed_start or parsed_end or search:
            trades = self.trade_repository.get_filtered(
                user_id=user_id,
                start_date=parsed_start,
                end_date=parsed_end,
                search=search,
            )
        else:
            trades = self.trade_repository.get_by_user_id(user_id)

        return self._enrich_trades(trades)

    def _parse_date(self, value: Union[date, str]) -> Optional[date]:
        """Parse date from string or return date object as-is."""
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def get_trades_by_etf(self, user_id: int, etf_code: str) -> List[Dict]:
        """Get trades for a specific ETF."""
        trades = self.trade_repository.get_by_user_and_etf(user_id, etf_code)
        return self._enrich_trades(trades)

    def _enrich_trades(self, trades: List[Trade]) -> List[Dict]:
        """Add ETF details to trade records."""
        result = []
        etf_cache: Dict[str, dict] = {}

        for trade in trades:
            trade_dict = trade.to_dict()
            if trade.etf_code not in etf_cache:
                etf = self.etf_repository.get_by_code(trade.etf_code)
                etf_cache[trade.etf_code] = etf.to_dict() if etf else None

            trade_dict["etf"] = etf_cache[trade.etf_code]
            result.append(trade_dict)

        return result

    def create_trade(
        self,
        user_id: int,
        etf_code: str,
        trade_type: str,
        quantity: int,
        price: float,
        trade_date: str,
        memo: Optional[str] = None,
    ) -> Tuple[Optional[Trade], Optional[str]]:
        """Create a new trade record."""
        # Validate ETF exists
        etf = self.etf_repository.get_by_code(etf_code)
        if not etf:
            return None, "指定されたETFが見つかりません"

        # Validate trade_type
        if trade_type not in ("buy", "sell"):
            return None, "取引種別は'buy'または'sell'である必要があります"

        # Validate quantity
        if quantity <= 0:
            return None, "数量は1以上である必要があります"

        # Validate price
        if price <= 0:
            return None, "価格は0より大きい必要があります"

        # Parse and validate date
        try:
            parsed_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
        except ValueError:
            return None, "日付の形式が不正です（YYYY-MM-DD）"

        if parsed_date > date.today():
            return None, "未来の日付は指定できません"

        # Create trade
        trade = Trade(
            user_id=user_id,
            etf_code=etf_code,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            trade_date=parsed_date,
            memo=memo,
        )

        try:
            self.trade_repository.create(trade)
            self._clear_portfolio_cache(user_id)
            return trade, None
        except Exception as e:
            self.trade_repository.rollback()
            return None, f"取引の登録に失敗しました: {str(e)}"

    def update_trade(
        self,
        user_id: int,
        trade_id: int,
        trade_type: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trade_date: Optional[str] = None,
        memo: Optional[str] = None,
    ) -> Tuple[Optional[Trade], Optional[str]]:
        """Update an existing trade record."""
        trade = self.trade_repository.get_by_id(trade_id)

        if not trade:
            return None, "取引が見つかりません"

        if trade.user_id != user_id:
            return None, "この取引を編集する権限がありません"

        # Update fields if provided
        if trade_type is not None:
            if trade_type not in ("buy", "sell"):
                return None, "取引種別は'buy'または'sell'である必要があります"
            trade.trade_type = trade_type

        if quantity is not None:
            if quantity <= 0:
                return None, "数量は1以上である必要があります"
            trade.quantity = quantity

        if price is not None:
            if price <= 0:
                return None, "価格は0より大きい必要があります"
            trade.price = price

        if trade_date is not None:
            try:
                parsed_date = datetime.strptime(trade_date, "%Y-%m-%d").date()
            except ValueError:
                return None, "日付の形式が不正です（YYYY-MM-DD）"
            if parsed_date > date.today():
                return None, "未来の日付は指定できません"
            trade.trade_date = parsed_date

        if memo is not None:
            trade.memo = memo

        try:
            self.trade_repository.update(trade)
            self._clear_portfolio_cache(user_id)
            return trade, None
        except Exception as e:
            self.trade_repository.rollback()
            return None, f"取引の更新に失敗しました: {str(e)}"

    def delete_trade(self, user_id: int, trade_id: int) -> Tuple[bool, Optional[str]]:
        """Delete a trade record."""
        trade = self.trade_repository.get_by_id(trade_id)

        if not trade:
            return False, "取引が見つかりません"

        if trade.user_id != user_id:
            return False, "この取引を削除する権限がありません"

        try:
            self.trade_repository.delete(trade)
            self._clear_portfolio_cache(user_id)
            return True, None
        except Exception as e:
            self.trade_repository.rollback()
            return False, f"取引の削除に失敗しました: {str(e)}"

    def get_trade_by_id(
        self, user_id: int, trade_id: int
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Get a single trade by ID."""
        trade = self.trade_repository.get_by_id(trade_id)

        if not trade:
            return None, "取引が見つかりません"

        if trade.user_id != user_id:
            return None, "この取引を参照する権限がありません"

        trade_dict = trade.to_dict()
        etf = self.etf_repository.get_by_code(trade.etf_code)
        trade_dict["etf"] = etf.to_dict() if etf else None

        return trade_dict, None
