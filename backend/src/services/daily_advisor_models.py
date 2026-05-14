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

    bucket: str  # "group_a" | "group_b" | "cash" | "other"
    target_pct: float
    actual_pct: float
    drift_pp: float
    warn_threshold_pp: float  # mechanical_rules.drift_warn_pp 由来（SSOT、必須）

    @property
    def is_warn(self) -> bool:
        return abs(self.drift_pp) > self.warn_threshold_pp


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

    kind: str  # "morning" | "evening" | "weekly" | "alert"  # 旧 "rebalance" は morning に統合
    today: date
    user_id: str
    strategy_revision: date
    benchmark: str

    # 配分閾値（strategy.mechanical_rules から注入。SSOT、必須）
    drift_ok_pp: float
    drift_warn_pp: float

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

    # リバランス計画（kind="morning" に統合: 配分テーブル・採用外保有・
    # 次回リバランス日カウントダウン・四半期末日の本日アクション表示用）
    rebalance_plan: Optional["RebalancePlan"] = None

    # その他
    extra: Dict[str, Any] = field(default_factory=dict)
