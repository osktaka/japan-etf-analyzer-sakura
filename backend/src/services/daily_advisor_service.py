"""Daily Advisor Service: 個人投資戦略の日次判定エンジン.

純関数群で構成し、TDDしやすく依存注入可能にする.
データクラスは daily_advisor_models.py に分離（CLAUDE.md 500行上限遵守）.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.services.daily_advisor_models import (
    AllocationDrift,
    BuyAction,
    NotificationContext,
    RuleTrigger,
    SellAction,
)
from src.services.strategy_loader import Strategy

logger = logging.getLogger(__name__)

# 夕方サマリ／朝リマインダー／概要セクションで共通利用する上位件数
TOP_N = 3

# Re-export for backward compatibility
__all__ = [
    "AllocationDrift",
    "BuyAction",
    "NotificationContext",
    "RuleTrigger",
    "SellAction",
    "TOP_N",
    "build_alert_context",
    "build_evening_context",
    "build_morning_context",
    "build_weekly_context",
    "classify_buckets",
    "compute_allocation_drift",
    "compute_alpha_vs_benchmark",
    "compute_return_from_history",
    "compute_top_n_actions",
    "context_to_payload",
    "evaluate_mechanical_rules",
    "is_weekly_review_day",
    "make_fingerprint",
]


def compute_top_n_actions(actions, holdings_snapshots, n: int = TOP_N) -> List[Dict[str, Any]]:
    """売買アクション一覧を金額降順で上位 n 件抽出し、テンプレ表示用 dict に整形.

    Args:
        actions: ``RebalanceAction`` 互換のイテラブル（``etf_code`` / ``amount`` 属性を持つ）.
        holdings_snapshots: ``HoldingSnapshot`` 互換のイテラブル（``etf_code`` / ``name`` 属性）.
            ``name`` 逆引き用. 該当 code が無ければ ``etf_code`` をそのまま name に使う.
        n: 抽出件数. デフォルト ``TOP_N`` (=3).

    Returns:
        ``[{"etf_code": str, "name": str, "amount": int}, ...]`` 形式のリスト.
        ``amount`` は ``int(round(a.amount))``（円）.
    """
    holdings_by_code = {h.etf_code: h for h in (holdings_snapshots or ())}
    ranked = sorted(actions or (), key=lambda a: a.amount, reverse=True)[:n]
    return [
        {
            "etf_code": a.etf_code,
            "name": (
                holdings_by_code[a.etf_code].name
                if a.etf_code in holdings_by_code
                else a.etf_code
            ),
            "amount": int(round(a.amount)),
        }
        for a in ranked
    ]


# ============================================================
# Pure date predicates
# ============================================================


def is_weekly_review_day(target: date) -> bool:
    """毎週金曜日."""
    return target.weekday() == 4  # Monday=0, Friday=4


# ============================================================
# Mechanical rule checks (pure functions)
# ============================================================


def make_fingerprint(
    *, occurred_on: date, rule_kind: str, code: Optional[str], user_id: str
) -> str:
    """同日同銘柄同ルールの重複抑止用fingerprint."""
    raw = f"{occurred_on.isoformat()}|{rule_kind}|{code or ''}|{user_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check_loss_cut(
    holding: Dict[str, Any],
    *,
    threshold_pct: float,
    min_holding_months: int,
    today: date,
    user_id: str,
) -> Optional[RuleTrigger]:
    """損切りルール: 取得単価比 threshold_pct 以下、かつ保有 >= min_holding_months."""
    pnl_pct = holding.get("unrealized_pnl_percent")
    holding_days = holding.get("holding_days", 0)
    code = holding.get("etf_code")
    if pnl_pct is None or code is None:
        return None
    # 最低保有期間（簡略化のため 30 日/月 で換算）
    # 例: min_holding_months=6 → 180日。テスト境界も同様の前提.
    if holding_days < min_holding_months * 30:
        return None
    if pnl_pct > threshold_pct:
        return None
    fp = make_fingerprint(
        occurred_on=today, rule_kind="loss_cut", code=code, user_id=user_id
    )
    return RuleTrigger(
        rule_kind="loss_cut",
        code=code,
        severity="critical",
        message=(
            f"{code}: 損切りライン到達 ({pnl_pct:+.2f}% <= {threshold_pct:.1f}%、"
            f"保有{holding_days}日)"
        ),
        fingerprint=fp,
        payload={
            "pnl_pct": pnl_pct,
            "threshold_pct": threshold_pct,
            "holding_days": holding_days,
        },
    )


def _check_take_profit(
    holding: Dict[str, Any],
    *,
    thresholds_pct: Tuple[float, ...],
    today: date,
    user_id: str,
) -> List[RuleTrigger]:
    """利確ルール: 第1段(50%)/第2段(100%)を別ruleとして発火."""
    triggers: List[RuleTrigger] = []
    pnl_pct = holding.get("unrealized_pnl_percent")
    code = holding.get("etf_code")
    if pnl_pct is None or code is None:
        return triggers
    for idx, t in enumerate(thresholds_pct, start=1):
        if pnl_pct >= t:
            kind = f"take_profit_{idx}"
            fp = make_fingerprint(
                occurred_on=today, rule_kind=kind, code=code, user_id=user_id
            )
            triggers.append(
                RuleTrigger(
                    rule_kind=kind,
                    code=code,
                    severity="info",
                    message=(
                        f"{code}: 利確第{idx}段到達 ({pnl_pct:+.2f}% >= "
                        f"{t:.1f}%)"
                    ),
                    fingerprint=fp,
                    payload={"pnl_pct": pnl_pct, "threshold_pct": t},
                )
            )
    return triggers


def _check_n225_drawdown(
    n225_change_pct: Optional[float],
    *,
    threshold_pct: float,
    today: date,
    user_id: str,
) -> Optional[RuleTrigger]:
    """N225 急落ルール: 前日終値比 threshold_pct 以下."""
    if n225_change_pct is None:
        return None
    if n225_change_pct > threshold_pct:
        return None
    fp = make_fingerprint(
        occurred_on=today, rule_kind="n225_drawdown", code=None, user_id=user_id
    )
    return RuleTrigger(
        rule_kind="n225_drawdown",
        code=None,
        severity="warn",
        message=(
            f"N225 急落: {n225_change_pct:+.2f}% (閾値 {threshold_pct:.1f}%)、"
            f"DCA前倒し検討"
        ),
        fingerprint=fp,
        payload={"change_pct": n225_change_pct, "threshold_pct": threshold_pct},
    )


def _check_min_holding_period(
    holding: Dict[str, Any], *, min_holding_months: int
) -> bool:
    """最低保有期間を満たすか（True=満たす、False=未到達）."""
    holding_days = holding.get("holding_days", 0)
    return holding_days >= min_holding_months * 30


def compute_allocation_drift(
    *,
    strategy: Strategy,
    actual_buckets: Dict[str, float],
) -> Tuple[AllocationDrift, ...]:
    """目標配分との差を計算.

    Args:
        strategy: target_buckets と mechanical_rules.drift_warn_pp を提供.
        actual_buckets: {"group_a": 0.45, "group_b": 0.45, "cash": 0.10, "other": 0.0}.

    Returns:
        各bucket(group_a/group_b/cash/other)のdrift（pp単位）.
        other は target=0% で扱い、保有があれば自動で逸脱として表示される.
    """
    warn_pp = strategy.mechanical_rules.drift_warn_pp
    drifts: List[AllocationDrift] = []
    # target_buckets に含まれる group_a/group_b/cash を順に処理.
    for bucket_key, bucket_def in strategy.target_buckets.items():
        actual = actual_buckets.get(bucket_key, 0.0)
        target = bucket_def.weight_pct / 100.0
        drift_pp = (actual - target) * 100.0
        drifts.append(
            AllocationDrift(
                bucket=bucket_key,
                target_pct=target * 100.0,
                actual_pct=actual * 100.0,
                drift_pp=round(drift_pp, 2),
                warn_threshold_pp=warn_pp,
            )
        )
    # other（採用外保有）: target=0%
    other_actual = actual_buckets.get("other", 0.0)
    if other_actual > 0.0:
        drifts.append(
            AllocationDrift(
                bucket="other",
                target_pct=0.0,
                actual_pct=other_actual * 100.0,
                drift_pp=round(other_actual * 100.0, 2),
                warn_threshold_pp=warn_pp,
            )
        )
    return tuple(drifts)


def _check_allocation_drift(
    drifts: Tuple[AllocationDrift, ...],
    *,
    threshold_pct: float,
    today: date,
    user_id: str,
) -> List[RuleTrigger]:
    """配分逸脱ルール."""
    triggers: List[RuleTrigger] = []
    for d in drifts:
        if abs(d.drift_pp) > threshold_pct:
            kind = "allocation_drift"
            code = d.bucket  # bucket名をcode代わりに使用（fingerprintで使う）
            fp = make_fingerprint(
                occurred_on=today, rule_kind=kind, code=code, user_id=user_id
            )
            triggers.append(
                RuleTrigger(
                    rule_kind=kind,
                    code=None,
                    severity="warn",
                    message=(
                        f"配分逸脱: {d.bucket} {d.actual_pct:.1f}% "
                        f"(目標 {d.target_pct:.1f}%, 差 {d.drift_pp:+.2f}pp)"
                    ),
                    fingerprint=fp,
                    payload={
                        "bucket": d.bucket,
                        "actual_pct": d.actual_pct,
                        "target_pct": d.target_pct,
                        "drift_pp": d.drift_pp,
                    },
                )
            )
    return triggers


# ============================================================
# Aggregator
# ============================================================


def evaluate_mechanical_rules(
    *,
    strategy: Strategy,
    holdings: List[Dict[str, Any]],
    n225_change_pct: Optional[float],
    allocation_drifts: Tuple[AllocationDrift, ...],
    today: date,
    user_id: str,
) -> Tuple[RuleTrigger, ...]:
    """全機械ルールを評価."""
    rules = strategy.mechanical_rules
    triggers: List[RuleTrigger] = []

    for h in holdings:
        # 損切り
        lc = _check_loss_cut(
            h,
            threshold_pct=rules.loss_cut_pct,
            min_holding_months=rules.min_holding_months,
            today=today,
            user_id=user_id,
        )
        if lc:
            triggers.append(lc)
        # 利確
        triggers.extend(
            _check_take_profit(
                h,
                thresholds_pct=rules.take_profit_pct,
                today=today,
                user_id=user_id,
            )
        )

    # N225 drawdown
    nd = _check_n225_drawdown(
        n225_change_pct,
        threshold_pct=rules.n225_drawdown_trigger_pct,
        today=today,
        user_id=user_id,
    )
    if nd:
        triggers.append(nd)

    # 配分逸脱
    triggers.extend(
        _check_allocation_drift(
            allocation_drifts,
            threshold_pct=rules.drift_warn_pp,
            today=today,
            user_id=user_id,
        )
    )

    return tuple(triggers)


# ============================================================
# Bucket classification
# ============================================================


def classify_buckets(
    *,
    holdings: List[Dict[str, Any]],
    cash_balance: float,
    strategy: Strategy,
) -> Dict[str, float]:
    """保有銘柄を group_a/group_b/cash/other に分類し、各bucketの構成比を返す.

    分類ルール:
    - 戦略の target_holdings で bucket=="group_a" の銘柄 → group_a
    - 戦略の target_holdings で bucket=="group_b" の銘柄 → group_b
    - 上記いずれにも含まれない保有銘柄 → "other"（採用外）
    - 現金 → "cash"
    """
    # 銘柄コード -> bucket dict（採用銘柄のみ）
    bucket_of: Dict[str, str] = {h.code: h.bucket for h in strategy.target_holdings}

    group_a_value = 0.0
    group_b_value = 0.0
    other_value = 0.0
    for h in holdings:
        code = h.get("etf_code")
        v = float(h.get("current_value", 0.0))
        bucket = bucket_of.get(code)
        if bucket == "group_a":
            group_a_value += v
        elif bucket == "group_b":
            group_b_value += v
        else:
            other_value += v

    total = group_a_value + group_b_value + other_value + cash_balance
    if total <= 0:
        return {"group_a": 0.0, "group_b": 0.0, "cash": 0.0, "other": 0.0}
    return {
        "group_a": group_a_value / total,
        "group_b": group_b_value / total,
        "cash": cash_balance / total,
        "other": other_value / total,
    }


# ============================================================
# Alpha vs Benchmark
# ============================================================


def compute_alpha_vs_benchmark(
    *,
    portfolio_return_pct: Optional[float],
    benchmark_return_pct: Optional[float],
) -> Optional[float]:
    """ポートフォリオ - ベンチマーク (pp)."""
    if portfolio_return_pct is None or benchmark_return_pct is None:
        return None
    return round(portfolio_return_pct - benchmark_return_pct, 2)


def compute_return_from_history(
    history: List[Dict[str, Any]],
    *,
    lookback_days: int = 5,
    value_key: str = "value",
) -> Optional[float]:
    """直近 lookback_days 営業日のリターン(%)を計算.

    Args:
        history: 時系列データ（昇順想定）。各要素は {value_key: float, ...}.
        lookback_days: 何営業日分のリターンを見るか.
        value_key: 値を取り出すキー.

    Returns:
        (latest - base) / base * 100. データ不足や base==0 は None.
    """
    if not history:
        return None
    # 最低 lookback_days+1 件（基準日 + 5営業日）必要
    if len(history) < lookback_days + 1:
        return None
    base = history[-(lookback_days + 1)].get(value_key)
    latest = history[-1].get(value_key)
    if base is None or latest is None:
        return None
    try:
        base_f = float(base)
        latest_f = float(latest)
    except (TypeError, ValueError):
        return None
    if base_f == 0:
        return None
    return round((latest_f - base_f) / base_f * 100.0, 2)


# ============================================================
# Context builders (re-export from daily_advisor_contexts)
# ============================================================

from src.services.daily_advisor_contexts import (  # noqa: E402
    build_alert_context,
    build_evening_context,
    build_morning_context,
    build_weekly_context,
)


# ============================================================
# Helpers
# ============================================================


def context_to_payload(ctx: NotificationContext) -> str:
    """NotificationContext を JSON 文字列にする（DB保存用）."""
    return json.dumps(asdict(ctx), default=str, ensure_ascii=False)
