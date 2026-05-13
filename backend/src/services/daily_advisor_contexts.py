"""通知コンテキストのbuilder群（kind別）.

daily_advisor_service.py から分離（500行上限遵守のため）.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.services.daily_advisor_models import (
    AllocationDrift,
    BuyAction,
    NotificationContext,
    RuleTrigger,
    SellAction,
)
from src.services.strategy_loader import (
    BuyAction as StrategyBuy,
    SellAction as StrategySell,
    Strategy,
)


def _to_sell_actions(strategy_sells: List[StrategySell]) -> Tuple[SellAction, ...]:
    return tuple(
        SellAction(
            code=s.code,
            name=s.name,
            quantity=s.quantity,
            action=s.action,
            reason=s.reason,
        )
        for s in strategy_sells
    )


def _to_buy_actions(strategy_buys: List[StrategyBuy]) -> Tuple[BuyAction, ...]:
    return tuple(BuyAction(code=b.code, quantity=b.quantity) for b in strategy_buys)


def build_morning_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    summary: Dict[str, Any],
    triggers: Tuple[RuleTrigger, ...] = (),
) -> NotificationContext:
    """朝のコンテキスト: 当日のアクション + 前日終値ベースの要約."""
    sells = strategy.get_sells_on(today)
    buys = strategy.get_buys_on(today)
    return NotificationContext(
        kind="morning",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        sells_today=_to_sell_actions(sells),
        buys_today=_to_buy_actions(buys),
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        daily_change_pct=summary.get("daily_change_total_asset_percent"),
        holdings_count=int(summary.get("holdings_count", 0)),
        triggers=triggers,
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
    return NotificationContext(
        kind="evening",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        daily_change_pct=summary.get("daily_change_total_asset_percent"),
        holdings_count=int(summary.get("holdings_count", 0)),
        allocation_drifts=drifts,
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
    return NotificationContext(
        kind="weekly",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        holdings_count=int(summary.get("holdings_count", 0)),
        allocation_drifts=drifts,
        triggers=triggers,
        alpha_pp=alpha,
        period_label=period_label,
        benchmark_return_pct=benchmark_return_pct,
        portfolio_return_pct=portfolio_return_pct,
    )


def build_rebalance_context(
    *,
    strategy: Strategy,
    today: date,
    user_id: str,
    summary: Dict[str, Any],
    rebalance_plan,
) -> NotificationContext:
    """リバランス通知のコンテキスト.

    PortfolioRebalanceService.calculate_rebalance_plan() の結果を保持.
    summary には PortfolioService.get_portfolio_summary() を渡す.
    """
    return NotificationContext(
        kind="rebalance",
        today=today,
        user_id=user_id,
        strategy_revision=strategy.revision,
        benchmark=strategy.benchmark,
        total_asset=float(summary.get("total_asset", 0.0)),
        total_value=float(summary.get("total_value", 0.0)),
        cash_balance=float(summary.get("cash_balance", 0.0)),
        daily_change_pct=summary.get("daily_change_total_asset_percent"),
        holdings_count=int(summary.get("holdings_count", 0)),
        rebalance_plan=rebalance_plan,
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
        triggers=triggers,
    )
