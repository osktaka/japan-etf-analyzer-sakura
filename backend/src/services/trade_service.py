"""Trade service for managing user's ETF transactions."""
from datetime import date, datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from src.models import Trade
from src.repositories.etf_repository import ETFRepository
from src.repositories.trade_repository import TradeRepository

if TYPE_CHECKING:
    from src.services.portfolio_service import PortfolioService


class TradeService:
    """Service for trade operations."""

    def __init__(
        self,
        trade_repository: Optional[TradeRepository] = None,
        etf_repository: Optional[ETFRepository] = None,
        portfolio_service: Optional["PortfolioService"] = None,
    ):
        """Initialize trade service."""
        self.trade_repository = trade_repository or TradeRepository()
        self.etf_repository = etf_repository or ETFRepository()
        self._portfolio_service = portfolio_service

    def _get_portfolio_service(self) -> "PortfolioService":
        """Lazily resolve PortfolioService (avoids import cycle at module load)."""
        if self._portfolio_service is None:
            from src.services.portfolio_service import PortfolioService

            self._portfolio_service = PortfolioService()
        return self._portfolio_service

    def _clear_portfolio_cache(self, user_id: int) -> None:
        """Clear portfolio-related cache after trade CUD operations."""
        # Avoid circular import by lazy import
        from src.services.portfolio_service import PortfolioService

        PortfolioService.clear_valuation_cache(user_id)

    def _validate_balance(
        self, user_id: int, etf_code: str, trade_type: str, quantity: int, price: float
    ) -> Optional[str]:
        """Reject trades that would overdraw cash or oversell holdings.

        分割調整済みの保有数量・現金は必ず PortfolioService 経由で取得する。
        trades.quantity を直接合算すると分割考慮漏れで誤判定するため禁止。
        """
        portfolio = self._get_portfolio_service()

        if trade_type == "buy":
            required = quantity * price
            summary = portfolio.get_portfolio_summary(user_id)
            cash_balance = summary.get("cash_balance", 0)
            if required > cash_balance:
                return (
                    f"現金残高が不足しています（必要額 {required:,.0f}円 / "
                    f"残高 {cash_balance:,.0f}円）"
                )
            return None

        # sell: 分割調整後の保有数量と比較
        holdings = portfolio.get_holdings(user_id)
        held = next(
            (h["quantity"] for h in holdings if h["etf_code"] == etf_code), 0
        )
        if quantity > held:
            return (
                f"保有数量を超える売却です（売却 {quantity} / "
                f"保有 {held:g}）"
            )
        return None

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

        balance_error = self._validate_balance(
            user_id, etf_code, trade_type, quantity, price
        )
        if balance_error:
            return None, balance_error

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
