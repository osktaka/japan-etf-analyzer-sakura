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

    # リバランス計画（kind="morning"/"evening" 両方で使用:
    # - evening: 銘柄別配分テーブル・採用外保有・売却/買付プランの本体表示
    # - morning: 次回リバランス日カウントダウン・四半期末日の本日アクション表示用
    # ※ 朝/夕構成見直し後は evening が「本体」、morning は要約のみ）
    rebalance_plan: Optional["RebalancePlan"] = None

    # 朝メール用: overnight 市況サマリ（米国指数・先物・USDJPY・VIX）
    # market_data_quick.fetch_overnight_data() の返り値 dict 形式
    overnight: Optional[Dict[str, Any]] = None

    # 朝メール用: 前夜の夕方バッチが残した決定事項サマリ JSON
    # evening 実行時に reports/test/daily-tasks/evening_summary_YYYYMMDD.json に
    # 保存され、翌朝の morning 実行時に読み込まれる
    previous_evening_summary: Optional[Dict[str, Any]] = None

    # 夕方メール用: 売買プラン概要セクション（常時表示）の top3 一覧.
    # ``filter_actions_for_display`` で表示用フィルタ（``DISPLAY_THRESHOLD_PP`` 未満
    # の採用済み銘柄を除外）を適用後、``compute_top_n_actions`` で金額降順上位 3 件.
    # rebalance_plan が None のときは空タプル（テンプレ側でセクションごと skip）.
    sell_top3: Tuple[Dict[str, Any], ...] = ()
    buy_top3: Tuple[Dict[str, Any], ...] = ()

    # 夕方メール用: 売買プラン概要セクションの「件数」表示用.
    # ``filter_actions_for_display`` 適用後のアクション件数（top3 と同じソース）.
    # テンプレ側の「売却 X 件 / 買付 Y 件」表示と top3 / 件数を一致させるために使用.
    # rebalance_plan が None のときは 0.
    sell_filtered_count: int = 0
    buy_filtered_count: int = 0

    # 夕方メール用: 詳細表（trade_actions_md/html）を表示する閾値（日数）.
    # ``rebalance_plan.is_rebalance_day`` または
    # ``rebalance_plan.days_to_next_rebalance <= rebalance_detail_threshold_days``
    # のときのみ詳細表を出す.
    rebalance_detail_threshold_days: int = 0

    # その他
    extra: Dict[str, Any] = field(default_factory=dict)
