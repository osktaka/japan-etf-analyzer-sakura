"""通知コンテキストのbuilder群（kind別）.

daily_advisor_service.py から分離（500行上限遵守のため）.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.services.daily_advisor_models import (
    AllocationDrift,
    NotificationContext,
    RuleTrigger,
)
from src.services.strategy_loader import Strategy

# 夕方メールで売買プラン「詳細表」を表示するかの閾値（基準日まで N 日以内）.
# is_rebalance_day も含めて条件付き表示する。
REBALANCE_DETAIL_THRESHOLD_DAYS = 3


def build_morning_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    summary: Dict[str, Any],
    rebalance_plan=None,
    triggers: Tuple[RuleTrigger, ...] = (),
    overnight: Optional[Dict[str, Any]] = None,
    previous_evening_summary: Optional[Dict[str, Any]] = None,
) -> NotificationContext:
    """朝のコンテキスト: 寄り付き前のアクション材料.

    朝/夕構成見直し後は以下の役割:
    - overnight: 米国指数・先物・為替・VIX の overnight サマリ（新規）
    - previous_evening_summary: 前夜の夕方バッチが残した決定事項リマインダー（新規）
    - rebalance_plan: 次回リバランス基準日のカウントダウン用に保持（要約のみ表示）
    - 銘柄別配分テーブル・売買プランの本体表示は evening へ移管

    Args:
        rebalance_plan: PortfolioRebalanceService.calculate_rebalance_plan() の結果.
            None の場合はリバランス情報なしで構築する.
        overnight: market_data_quick.fetch_overnight_data() の返り値 dict.
            None の場合は overnight セクションを表示しない.
        previous_evening_summary: 前夜の evening_summary_YYYYMMDD.json を
            読み込んだ dict. None の場合はリマインダー欄をスキップする.
    """
    return NotificationContext(
        kind="morning",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        drift_ok_pp=strategy.mechanical_rules.drift_ok_pp,
        drift_warn_pp=strategy.mechanical_rules.drift_warn_pp,
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        daily_change_pct=summary.get("daily_change_total_asset_percent"),
        holdings_count=int(summary.get("holdings_count", 0)),
        triggers=triggers,
        rebalance_plan=rebalance_plan,
        overnight=overnight,
        previous_evening_summary=previous_evening_summary,
    )


def _normalize_drifts(
    drifts: Tuple[AllocationDrift, ...],
    *,
    warn_threshold_pp: float,
) -> Tuple[AllocationDrift, ...]:
    """drifts の warn_threshold_pp を strategy 由来の値で揃える.

    呼び出し元（advisor_runner / dry-run / テスト）が strategy 渡しの
    compute_allocation_drift を経由していれば既に正しい値が入っているが、
    防御的に上書きする.
    """
    return tuple(
        AllocationDrift(
            bucket=d.bucket,
            target_pct=d.target_pct,
            actual_pct=d.actual_pct,
            drift_pp=d.drift_pp,
            warn_threshold_pp=warn_threshold_pp,
        )
        for d in drifts
    )


def build_evening_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    summary: Dict[str, Any],
    drifts: Tuple[AllocationDrift, ...],
    triggers: Tuple[RuleTrigger, ...],
    rebalance_plan=None,
) -> NotificationContext:
    """夕方のコンテキスト: 当日終値ベース + 配分・トリガー + リバランス計画.

    朝/夕構成見直しにより、銘柄別配分テーブル・採用外保有・売却/買付プランの
    本体表示はこちらに集約される.

    2026-05-XX 段階表示再構成:
    - 売買プラン「概要」セクション（件数 + top3）は常時表示
    - 売買プラン「詳細表」セクションは基準日まで
      ``REBALANCE_DETAIL_THRESHOLD_DAYS`` 日以内、もしくは ``is_rebalance_day``
      のときのみ表示。テンプレ側で ``rebalance_detail_threshold_days`` を見て分岐.

    Args:
        rebalance_plan: PortfolioRebalanceService.calculate_rebalance_plan() の結果.
            None の場合はリバランス情報なしで構築する.
    """
    # 循環import 回避: 関数内 import
    from src.services.daily_advisor_service import compute_top_n_actions

    warn_pp = strategy.mechanical_rules.drift_warn_pp
    normalized = _normalize_drifts(drifts, warn_threshold_pp=warn_pp)
    if rebalance_plan is not None:
        sell_top3 = tuple(
            compute_top_n_actions(
                rebalance_plan.sell_actions, rebalance_plan.holdings_snapshots
            )
        )
        buy_top3 = tuple(
            compute_top_n_actions(
                rebalance_plan.buy_actions, rebalance_plan.holdings_snapshots
            )
        )
    else:
        sell_top3 = ()
        buy_top3 = ()
    return NotificationContext(
        kind="evening",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        drift_ok_pp=strategy.mechanical_rules.drift_ok_pp,
        drift_warn_pp=warn_pp,
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        daily_change_pct=summary.get("daily_change_total_asset_percent"),
        holdings_count=int(summary.get("holdings_count", 0)),
        allocation_drifts=normalized,
        triggers=triggers,
        rebalance_plan=rebalance_plan,
        sell_top3=sell_top3,
        buy_top3=buy_top3,
        rebalance_detail_threshold_days=REBALANCE_DETAIL_THRESHOLD_DAYS,
    )


def build_weekly_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    summary: Dict[str, Any],
    drifts: Tuple[AllocationDrift, ...],
    triggers: Tuple[RuleTrigger, ...],
    portfolio_return_pct: Optional[float],
    benchmark_return_pct: Optional[float],
    period_label: str = "過去5営業日",
) -> NotificationContext:
    """週次のコンテキスト."""
    # 循環import回避: 関数内 import
    from src.services.daily_advisor_service import compute_alpha_vs_benchmark

    alpha = compute_alpha_vs_benchmark(
        portfolio_return_pct=portfolio_return_pct,
        benchmark_return_pct=benchmark_return_pct,
    )
    warn_pp = strategy.mechanical_rules.drift_warn_pp
    normalized = _normalize_drifts(drifts, warn_threshold_pp=warn_pp)
    return NotificationContext(
        kind="weekly",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        drift_ok_pp=strategy.mechanical_rules.drift_ok_pp,
        drift_warn_pp=warn_pp,
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        holdings_count=int(summary.get("holdings_count", 0)),
        allocation_drifts=normalized,
        triggers=triggers,
        alpha_pp=alpha,
        period_label=period_label,
        benchmark_return_pct=benchmark_return_pct,
        portfolio_return_pct=portfolio_return_pct,
    )


def build_alert_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    triggers: Tuple[RuleTrigger, ...],
) -> NotificationContext:
    """アラート（watcher用）コンテキスト."""
    return NotificationContext(
        kind="alert",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        drift_ok_pp=strategy.mechanical_rules.drift_ok_pp,
        drift_warn_pp=strategy.mechanical_rules.drift_warn_pp,
        triggers=triggers,
    )
