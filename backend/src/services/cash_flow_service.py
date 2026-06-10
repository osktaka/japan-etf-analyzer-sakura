"""CashFlow service for managing user's deposit/withdrawal transactions."""
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from src.models import CashFlow
from src.repositories.cash_flow_repository import CashFlowRepository


class CashFlowService:
    """Service for cash flow operations."""

    def __init__(
        self,
        cash_flow_repository: Optional[CashFlowRepository] = None,
    ):
        """Initialize cash flow service."""
        self.cash_flow_repository = cash_flow_repository or CashFlowRepository()

    def _clear_portfolio_cache(self, user_id: int) -> None:
        """Clear portfolio-related cache after cash flow CUD operations."""
        # Avoid circular import by lazy import
        from src.services.portfolio_service import PortfolioService

        PortfolioService.clear_valuation_cache(user_id)

    def get_user_cash_flows(self, user_id: int) -> List[Dict]:
        """Get all cash flows for a user.

        Returns:
            List of cash flow dicts
        """
        cash_flows = self.cash_flow_repository.get_by_user_id(user_id)
        return [cf.to_dict() for cf in cash_flows]

    def get_cash_flows_by_date_range(
        self,
        user_id: int,
        start_date: str = None,
        end_date: str = None,
    ) -> List[Dict]:
        """Get cash flows within a date range.

        Args:
            user_id: User ID
            start_date: Start date string (YYYY-MM-DD), optional
            end_date: End date string (YYYY-MM-DD), optional

        Returns:
            List of cash flow dicts
        """
        parsed_start = self._parse_date(start_date) if start_date else None
        parsed_end = self._parse_date(end_date) if end_date else None

        if parsed_start or parsed_end:
            cash_flows = self.cash_flow_repository.get_by_date_range(
                user_id, parsed_start, parsed_end
            )
        else:
            cash_flows = self.cash_flow_repository.get_by_user_id(user_id)

        return [cf.to_dict() for cf in cash_flows]

    def _parse_date(self, value) -> Optional[date]:
        """Parse date from string or return date object as-is."""
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def create_cash_flow(
        self,
        user_id: int,
        flow_type: str,
        amount: float,
        flow_date: str,
        memo: Optional[str] = None,
    ) -> Tuple[Optional[CashFlow], Optional[str]]:
        """Create a new cash flow record."""
        # Validate flow_type
        if flow_type not in ("deposit", "withdrawal"):
            return None, "入出金種別は'deposit'または'withdrawal'である必要があります"

        # Validate amount
        if amount <= 0:
            return None, "金額は0より大きい必要があります"

        # Parse and validate date
        try:
            parsed_date = datetime.strptime(flow_date, "%Y-%m-%d").date()
        except ValueError:
            return None, "日付の形式が不正です（YYYY-MM-DD）"

        if parsed_date > date.today():
            return None, "未来の日付は指定できません"

        if flow_type == "withdrawal":
            from src.services.portfolio_service import PortfolioService

            summary = PortfolioService().get_portfolio_summary(user_id)
            cash_balance = summary.get("cash_balance", 0)
            if amount > cash_balance:
                return None, (
                    f"現金残高を超える出金です（出金 {amount:,.0f}円 / "
                    f"残高 {cash_balance:,.0f}円）"
                )

        # Create cash flow
        cash_flow = CashFlow(
            user_id=user_id,
            flow_type=flow_type,
            amount=amount,
            flow_date=parsed_date,
            memo=memo,
        )

        try:
            self.cash_flow_repository.create(cash_flow)
            self._clear_portfolio_cache(user_id)
            return cash_flow, None
        except Exception as e:
            self.cash_flow_repository.rollback()
            return None, f"入出金の登録に失敗しました: {str(e)}"

    def update_cash_flow(
        self,
        user_id: int,
        cash_flow_id: int,
        flow_type: Optional[str] = None,
        amount: Optional[float] = None,
        flow_date: Optional[str] = None,
        memo: Optional[str] = None,
    ) -> Tuple[Optional[CashFlow], Optional[str]]:
        """Update an existing cash flow record."""
        cash_flow = self.cash_flow_repository.get_by_id(cash_flow_id)

        if not cash_flow:
            return None, "入出金記録が見つかりません"

        if cash_flow.user_id != user_id:
            return None, "この入出金記録を編集する権限がありません"

        # Update fields if provided
        if flow_type is not None:
            if flow_type not in ("deposit", "withdrawal"):
                return None, "入出金種別は'deposit'または'withdrawal'である必要があります"
            cash_flow.flow_type = flow_type

        if amount is not None:
            if amount <= 0:
                return None, "金額は0より大きい必要があります"
            cash_flow.amount = amount

        if flow_date is not None:
            try:
                parsed_date = datetime.strptime(flow_date, "%Y-%m-%d").date()
            except ValueError:
                return None, "日付の形式が不正です（YYYY-MM-DD）"
            if parsed_date > date.today():
                return None, "未来の日付は指定できません"
            cash_flow.flow_date = parsed_date

        if memo is not None:
            cash_flow.memo = memo

        try:
            self.cash_flow_repository.update(cash_flow)
            self._clear_portfolio_cache(user_id)
            return cash_flow, None
        except Exception as e:
            self.cash_flow_repository.rollback()
            return None, f"入出金の更新に失敗しました: {str(e)}"

    def delete_cash_flow(
        self, user_id: int, cash_flow_id: int
    ) -> Tuple[bool, Optional[str]]:
        """Delete a cash flow record."""
        cash_flow = self.cash_flow_repository.get_by_id(cash_flow_id)

        if not cash_flow:
            return False, "入出金記録が見つかりません"

        if cash_flow.user_id != user_id:
            return False, "この入出金記録を削除する権限がありません"

        try:
            self.cash_flow_repository.delete(cash_flow)
            self._clear_portfolio_cache(user_id)
            return True, None
        except Exception as e:
            self.cash_flow_repository.rollback()
            return False, f"入出金の削除に失敗しました: {str(e)}"
