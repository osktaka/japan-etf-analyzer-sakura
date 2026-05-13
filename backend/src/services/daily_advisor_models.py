"""Daily Advisor のデータクラス定義（純粋データ、依存ゼロ）.

本体 (daily_advisor_service.py) が500行を超えないよう分離.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.portfolio_rebalance_service import RebalancePlan


@dataclass(frozen=True)
class SellAction:
    """通知用売却アクション."""

    code: str
    name: str
    quantity: int
    action: str
    reason: str


@dataclass(frozen=True)
class BuyAction:
    """通知用買付アクション."""

    code: str
    quantity: int


@dataclass(frozen=True)
class AllocationDrift:
    """配分逸脱."""

    bucket: str  # "core" | "theme" | "cash"
    target_pct: float
    actual_pct: float
    drift_pp: float

    @property
    def is_warn(self) -> bool:
        return abs(self.drift_pp) > 5.0


@dataclass(frozen=True)
class RuleTrigger:
    """機械ルール発動."""

    rule_kind: str  # "loss_cut" | "take_profit_1" | ... | "allocation_drift"
    code: Optional[str]
    severity: str  # "info" | "warn" | "critical"
    message: str
    fingerprint: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotificationContext:
    """通知レンダリング用のコンテキスト."""

    kind: str  # "morning" | "evening" | "weekly" | "alert"
    today: date
    user_id: str
    strategy_revision: date
    benchmark: str

    # 当日アクション
    sells_today: Tuple[SellAction, ...] = ()
    buys_today: Tuple[BuyAction, ...] = ()

    # 保有・配分
    total_asset: float = 0.0
    total_value: float = 0.0
    cash_balance: float = 0.0
    daily_change_pct: Optional[float] = None
    holdings_count: int = 0
    allocation_drifts: Tuple[AllocationDrift, ...] = ()

    # ルール発動
    triggers: Tuple[RuleTrigger, ...] = ()

    # 週次/α
    alpha_pp: Optional[float] = None
    period_label: Optional[str] = None
    benchmark_return_pct: Optional[float] = None
    portfolio_return_pct: Optional[float] = None

    # 月初比（リード文の「文脈」行で使用）
    month_start_total_asset: Optional[float] = None
    month_start_change_pct: Optional[float] = None

    # リバランス計画（kind="rebalance" のみ使用）
    rebalance_plan: Optional["RebalancePlan"] = None

    # その他
    extra: Dict[str, Any] = field(default_factory=dict)
