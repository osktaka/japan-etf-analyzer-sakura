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


def build_morning_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    summary: Dict[str, Any],
    rebalance_plan=None,
    triggers: Tuple[RuleTrigger, ...] = (),
) -> NotificationContext:
    """朝のコンテキスト: 前日終値ベースの要約 + リバランス計画統合.

    Step 4 で旧 sell_schedule/buy_dca_schedule の代替として
    PortfolioRebalanceService.calculate_rebalance_plan() の結果を統合する.

    - 通常日: rebalance_plan は配分テーブル・採用外保有・カウントダウンの表示用
    - 四半期末日 (is_rebalance_day=True): sell_actions/buy_actions の本日実行案内も表示

    Args:
        rebalance_plan: PortfolioRebalanceService.calculate_rebalance_plan() の結果.
            None の場合はリバランス情報なしで構築する.
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
) -> NotificationContext:
    """夕方のコンテキスト: 当日終値ベース + 配分・トリガー."""
    warn_pp = strategy.mechanical_rules.drift_warn_pp
    normalized = _normalize_drifts(drifts, warn_threshold_pp=warn_pp)
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
