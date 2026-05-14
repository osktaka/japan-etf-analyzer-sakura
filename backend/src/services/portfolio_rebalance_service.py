"""ポートフォリオ・リバランス計算サービス.

戦略SSOT (docs/12_personal_strategy.md) の `target_holdings` / `target_buckets`
/ `mechanical_rules.drift_*` に従って、現状からの乖離 + 売買アクション案 +
次回リバランス基準日を算出する.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from src.services.strategy_loader import Strategy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RebalanceAction:
    """売買アクション1件."""

    etf_code: str
    action_type: str  # "sell" | "buy"
    quantity: int
    amount: float
    reason: str


@dataclass(frozen=True)
class HoldingSnapshot:
    """銘柄別保有スナップショット（テンプレ描画用）."""

    etf_code: str
    name: str
    quantity: float
    current_price: float
    current_value: float
    pnl_pct: Optional[float]
    target_pct: float
    actual_pct: float
    drift_pp: float
    classification: str  # "OK" | "WARN" | "CRITICAL"
    is_adopted: bool  # 採用8銘柄 or 採用外保有


@dataclass(frozen=True)
class RebalancePlan:
    """リバランス計算結果.

    Attributes:
        target_weights: 採用銘柄の目標配分（%、CASHは含めない）。
            合計はリスク資産分（90%）。CASH 目標は target_cash 等を参照。
        current_weights: 採用銘柄＋採用外保有銘柄＋CASH の actual_pct 辞書（%）。
            すなわち「実際に保有している全コード + CASH」を網羅し、
            合計はおおむね100%（小数誤差・端数調整を除く）になる。
            テンプレで採用銘柄のみに絞りたい場合は ``target_weights`` のキーで
            フィルタするか、``holdings_snapshots`` の ``is_adopted`` を使う。
        deviations: 各code → drift_pp（actual_pct - target_pct）。
            採用外銘柄では target_pct=0 のため drift_pp == actual_pct となる。
    """

    target_weights: Dict[str, float]
    current_weights: Dict[str, float]
    deviations: Dict[str, float]
    sell_actions: Tuple[RebalanceAction, ...]
    buy_actions: Tuple[RebalanceAction, ...]
    total_asset: float
    target_cash: float
    target_cash_pct: float  # 目標現金比率（%）。strategy.target_buckets["cash"].weight_pct
    current_cash: float
    cash_deviation_pp: float
    days_to_next_rebalance: int
    next_rebalance_date: date
    is_rebalance_day: bool
    daily_pnl_pct: Optional[float]
    holdings_snapshots: Tuple[HoldingSnapshot, ...] = field(default_factory=tuple)
    warn_count: int = 0
    critical_count: int = 0


class PortfolioRebalanceService:
    """リバランス計算サービス（strategy 駆動）."""

    def __init__(self, strategy: "Strategy", portfolio_service=None):
        """
        Args:
            strategy: Strategy インスタンス（SSOT、必須）
            portfolio_service: PortfolioService（テスト時のみ注入）
        """
        self.strategy = strategy

        # 整合性チェック: target_holdings の weight_pct 合計 + cash = 100
        holdings_sum = sum(h.weight_pct for h in strategy.target_holdings)
        cash_pct = strategy.target_buckets["cash"].weight_pct
        total = holdings_sum + cash_pct
        if abs(total - 100.0) >= 0.001:
            raise ValueError(
                f"target_holdings weight_pct sum ({holdings_sum}) + cash "
                f"({cash_pct}) must equal 100.0, got {total}"
            )

        if portfolio_service is None:
            from src.services.portfolio_service import PortfolioService
            portfolio_service = PortfolioService()
        self.portfolio_service = portfolio_service

    # ------------------------------------------------------------
    # ヘルパ（strategy 経由の参照）
    # ------------------------------------------------------------
    @property
    def _adopted_target_pct(self) -> Dict[str, float]:
        """採用銘柄 code → target_pct."""
        return {h.code: h.weight_pct for h in self.strategy.target_holdings}

    @property
    def _adopted_names(self) -> Dict[str, str]:
        """採用銘柄 code → 表示名."""
        return {h.code: h.name for h in self.strategy.target_holdings}

    @property
    def _cash_target_pct(self) -> float:
        return self.strategy.target_buckets["cash"].weight_pct

    @property
    def _drift_ok_pp(self) -> float:
        return self.strategy.mechanical_rules.drift_ok_pp

    @property
    def _drift_warn_pp(self) -> float:
        return self.strategy.mechanical_rules.drift_warn_pp

    # ------------------------------------------------------------
    # メイン API
    # ------------------------------------------------------------
    def calculate_rebalance_plan(
        self,
        user_id: int,
        as_of_date: Optional[date] = None,
    ) -> RebalancePlan:
        """user_id のリバランス計画を計算.

        Args:
            user_id: users.id (int)
            as_of_date: 基準日（テスト用、デフォルトは today）

        Returns:
            RebalancePlan
        """
        today = as_of_date or date.today()

        holdings = self.portfolio_service.get_holdings(user_id)
        summary = self.portfolio_service.get_portfolio_summary(user_id)

        total_asset = float(summary.get("total_asset") or 0.0)
        current_cash = float(summary.get("cash_balance") or 0.0)
        daily_pnl_pct = summary.get("daily_change_total_asset_percent")

        holdings_by_code: Dict[str, Dict] = {h["etf_code"]: h for h in holdings}

        adopted_target_pct = self._adopted_target_pct
        adopted_names = self._adopted_names
        cash_target_pct = self._cash_target_pct

        target_cash = total_asset * (cash_target_pct / 100.0)
        cash_actual_pct = (
            (current_cash / total_asset * 100.0) if total_asset > 0 else 0.0
        )
        cash_deviation_pp = cash_actual_pct - cash_target_pct

        sell_actions: List[RebalanceAction] = []
        buy_actions: List[RebalanceAction] = []
        buy_candidates: List[Dict[str, float]] = []
        snapshots: List[HoldingSnapshot] = []
        deviations: Dict[str, float] = {}

        # --- 採用銘柄の処理 ---
        for code, target_pct in adopted_target_pct.items():
            target_amount = total_asset * (target_pct / 100.0)

            h = holdings_by_code.get(code)
            if h is None:
                current_price = 0.0
                current_value = 0.0
                quantity_held = 0.0
                pnl_pct = None
            else:
                current_price = float(h.get("current_price") or 0.0)
                current_value = float(h.get("current_value") or 0.0)
                quantity_held = float(h.get("quantity") or 0.0)
                pnl_pct = h.get("unrealized_pnl_percent")

            actual_pct = (
                (current_value / total_asset * 100.0) if total_asset > 0 else 0.0
            )
            drift_pp = actual_pct - target_pct
            deviations[code] = drift_pp
            classification = self._classify_drift(drift_pp)

            diff_amount = target_amount - current_value
            reason_text = (
                f"目標{target_pct:.2f}%・"
                f"現状{actual_pct:.2f}% "
                f"(乖離{drift_pp:+.2f}pp)"
            )
            if current_price > 0 and abs(diff_amount) >= current_price:
                qty = int(math.floor(abs(diff_amount) / current_price))
                trade_amount = qty * current_price
                if diff_amount > 0 and qty > 0:
                    buy_candidates.append(
                        {
                            "etf_code": code,
                            "qty": qty,
                            "amount": trade_amount,
                            "current_price": current_price,
                            "reason": reason_text,
                        }
                    )
                elif diff_amount < 0 and qty > 0:
                    sell_actions.append(
                        RebalanceAction(
                            etf_code=code,
                            action_type="sell",
                            quantity=qty,
                            amount=trade_amount,
                            reason=reason_text,
                        )
                    )

            snapshots.append(
                HoldingSnapshot(
                    etf_code=code,
                    name=adopted_names.get(code, code),
                    quantity=quantity_held,
                    current_price=current_price,
                    current_value=current_value,
                    pnl_pct=pnl_pct,
                    target_pct=target_pct,
                    actual_pct=actual_pct,
                    drift_pp=drift_pp,
                    classification=classification,
                    is_adopted=True,
                )
            )

        # --- 採用外保有銘柄の処理（全量売却推奨） ---
        adopted_codes = set(adopted_target_pct.keys())
        for code, h in holdings_by_code.items():
            if code in adopted_codes:
                continue
            quantity_held = float(h.get("quantity") or 0.0)
            if quantity_held <= 0:
                continue
            current_price = float(h.get("current_price") or 0.0)
            current_value = float(h.get("current_value") or 0.0)
            actual_pct = (
                (current_value / total_asset * 100.0)
                if total_asset > 0
                else 0.0
            )
            target_pct = 0.0
            drift_pp = actual_pct
            deviations[code] = drift_pp

            qty_int = int(round(quantity_held))
            fractional_remainder = abs(quantity_held - qty_int)
            if fractional_remainder >= 0.01:
                logger.warning(
                    "Non-adopted holding %s has fractional remainder %.4f "
                    "(quantity_held=%.4f, rounded=%d); rounded for sell action",
                    code,
                    fractional_remainder,
                    quantity_held,
                    qty_int,
                )
            if qty_int > 0:
                sell_actions.append(
                    RebalanceAction(
                        etf_code=code,
                        action_type="sell",
                        quantity=qty_int,
                        amount=current_value,
                        reason="採用外銘柄・全量売却",
                    )
                )

            etf_info = h.get("etf") or {}
            display_name = etf_info.get("name") or code

            snapshots.append(
                HoldingSnapshot(
                    etf_code=code,
                    name=display_name,
                    quantity=quantity_held,
                    current_price=current_price,
                    current_value=current_value,
                    pnl_pct=h.get("unrealized_pnl_percent"),
                    target_pct=target_pct,
                    actual_pct=actual_pct,
                    drift_pp=drift_pp,
                    classification="CRITICAL",
                    is_adopted=False,
                )
            )

        # --- 買付予算制約: リスク資産買付総額 ≤ 現金 + 売却額 - 目標現金 ---
        sum_sell_amount = sum(a.amount for a in sell_actions)
        cash_budget = current_cash + sum_sell_amount - target_cash
        sum_buy_amount_raw = sum(c["amount"] for c in buy_candidates)

        if sum_buy_amount_raw > cash_budget and sum_buy_amount_raw > 0:
            ratio = (
                max(0.0, cash_budget / sum_buy_amount_raw)
                if sum_buy_amount_raw > 0
                else 0.0
            )
            logger.warning(
                "Buy total %.0f exceeds cash budget %.0f "
                "(current_cash=%.0f + sell=%.0f - target_cash=%.0f); "
                "scaling buy candidates by ratio=%.4f",
                sum_buy_amount_raw,
                cash_budget,
                current_cash,
                sum_sell_amount,
                target_cash,
                ratio,
            )
            for c in buy_candidates:
                capped_amount = c["amount"] * ratio
                price = c["current_price"]
                qty = int(math.floor(capped_amount / price)) if price > 0 else 0
                if qty <= 0:
                    continue
                trade_amount = qty * price
                buy_actions.append(
                    RebalanceAction(
                        etf_code=c["etf_code"],
                        action_type="buy",
                        quantity=qty,
                        amount=trade_amount,
                        reason=c["reason"] + " ※予算制約で縮小",
                    )
                )
        else:
            for c in buy_candidates:
                buy_actions.append(
                    RebalanceAction(
                        etf_code=c["etf_code"],
                        action_type="buy",
                        quantity=int(c["qty"]),
                        amount=c["amount"],
                        reason=c["reason"],
                    )
                )

        # 整合性チェック: target_weights の合計（CASH除く） + CASH = 100
        target_weights: Dict[str, float] = dict(adopted_target_pct)
        _adopted_sum = sum(target_weights.values()) + cash_target_pct
        if abs(_adopted_sum - 100.0) >= 0.001:
            raise ValueError(
                f"target_weights + CASH must sum to 100.0, got {_adopted_sum}"
            )

        # 現在配分（採用銘柄＋現金）
        current_weights: Dict[str, float] = {
            s.etf_code: s.actual_pct for s in snapshots
        }
        current_weights["CASH"] = cash_actual_pct

        # 次回リバランス日
        next_date = self._next_rebalance_date(today)
        days_to_next = (next_date - today).days
        is_rebalance_day = days_to_next == 0

        # warn/critical 件数
        warn_count = sum(1 for s in snapshots if s.classification == "WARN")
        critical_count = sum(
            1 for s in snapshots if s.classification == "CRITICAL"
        )
        if abs(cash_deviation_pp) >= self._drift_warn_pp:
            critical_count += 1
        elif abs(cash_deviation_pp) >= self._drift_ok_pp:
            warn_count += 1

        return RebalancePlan(
            target_weights=target_weights,
            current_weights=current_weights,
            deviations=deviations,
            sell_actions=tuple(sell_actions),
            buy_actions=tuple(buy_actions),
            total_asset=total_asset,
            target_cash=target_cash,
            target_cash_pct=cash_target_pct,
            current_cash=current_cash,
            cash_deviation_pp=cash_deviation_pp,
            days_to_next_rebalance=days_to_next,
            next_rebalance_date=next_date,
            is_rebalance_day=is_rebalance_day,
            daily_pnl_pct=(
                float(daily_pnl_pct) if daily_pnl_pct is not None else None
            ),
            holdings_snapshots=tuple(snapshots),
            warn_count=warn_count,
            critical_count=critical_count,
        )

    # ------------------------------------------------------------
    # ヘルパ
    # ------------------------------------------------------------
    def _classify_drift(self, deviation_pp: float) -> str:
        """個別銘柄の乖離 → 分類."""
        abs_dev = abs(deviation_pp)
        if abs_dev < self._drift_ok_pp:
            return "OK"
        if abs_dev < self._drift_warn_pp:
            return "WARN"
        return "CRITICAL"

    @staticmethod
    def _next_rebalance_date(today: date) -> date:
        """今日以降の最近の四半期末月（3/6/9/12）の最終営業日を返す.

        - 当日が四半期末月の最終営業日ならそれを返す
        - 土日・祝日は除外（jpholiday）
        """
        try:
            import jpholiday
        except ImportError:
            logger.warning(
                "jpholiday is not installed; Japanese holidays will be "
                "treated as business days. Install via `pip install jpholiday` "
                "for accurate quarter-end business day calculation."
            )
            jpholiday = None  # type: ignore[assignment]

        def is_business_day(d: date) -> bool:
            if d.weekday() >= 5:
                return False
            if jpholiday is not None and jpholiday.is_holiday(d):
                return False
            return True

        def last_business_day_of_month(year: int, month: int) -> date:
            if month == 12:
                first_next = date(year + 1, 1, 1)
            else:
                first_next = date(year, month + 1, 1)
            d = first_next - timedelta(days=1)
            while not is_business_day(d):
                d -= timedelta(days=1)
            return d

        quarter_months = [3, 6, 9, 12]
        candidates: List[date] = []
        for m in quarter_months:
            candidates.append(last_business_day_of_month(today.year, m))
        candidates.append(last_business_day_of_month(today.year + 1, 3))

        for c in candidates:
            if c >= today:
                return c
        return candidates[-1]
