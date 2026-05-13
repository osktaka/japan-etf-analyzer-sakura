"""ポートフォリオ・リバランス計算サービス.

8銘柄目標配分（A群=45% + B群=45% + 現金=10%）に対して、現状からの乖離 +
売買アクション案 + 次回リバランス基準日を算出する.

設計詳細は計画ファイル `~/.claude/plans/silly-riding-babbage.md` を参照.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# 目標配分（合計100.00%、現金10%確保）
#   A群=45%（2559 / 1540 / 200A 各15%）
#   B群=45%（1306 / 1629 / 1615 / 2646 / 1618 各9.00%）
#   現金=10%
# ----------------------------------------------------------------------------
TARGET_ALLOCATION: Dict[str, float] = {
    # A群（逆相関3資産・各15%）
    "2559": 15.00,  # オルカン
    "1540": 15.00,  # 純金
    "200A": 15.00,  # 半導体
    # B群（日本株テーマ5資産・各9.00%）
    "1306": 9.00,  # TOPIX
    "1629": 9.00,  # 商社
    "1615": 9.00,  # 銀行
    "2646": 9.00,  # メタル
    "1618": 9.00,  # エネルギー資源
    # 現金
    "CASH": 10.00,
}

# 整合性チェック（モジュール ロード時に1度だけ実行）
# `python -O` で assert が無効化されても落とせるよう、明示的に ValueError を投げる。
_TOTAL_PCT = sum(TARGET_ALLOCATION.values())
if abs(_TOTAL_PCT - 100.0) >= 0.001:
    raise ValueError(
        f"TARGET_ALLOCATION must sum to 100.0, got {_TOTAL_PCT}"
    )

# 逸脱閾値（pp = percentage point）
DRIFT_OK_PP = 3.0
DRIFT_WARN_PP = 5.0

# 銘柄表示名（DB照会が不要な範囲で。詳細は etfs テーブル参照）
ETF_DISPLAY_NAMES: Dict[str, str] = {
    "2559": "オルカン",
    "1540": "純金",
    "200A": "半導体",
    "1306": "TOPIX",
    "1629": "商社",
    "1615": "銀行",
    "2646": "メタル",
    "1618": "エネルギー資源",
}


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
        target_weights: 採用8銘柄の目標配分（%、CASHは含めない）。
            合計はリスク資産90%。CASH目標は ``TARGET_ALLOCATION['CASH']`` 参照。
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
    deviations: Dict[str, float]  # 各code -> drift_pp（actual - target）
    sell_actions: Tuple[RebalanceAction, ...]
    buy_actions: Tuple[RebalanceAction, ...]
    total_asset: float
    target_cash: float
    current_cash: float
    cash_deviation_pp: float
    days_to_next_rebalance: int
    next_rebalance_date: date
    is_rebalance_day: bool
    daily_pnl_pct: Optional[float]
    # テンプレ描画用の追加情報
    holdings_snapshots: Tuple[HoldingSnapshot, ...] = field(default_factory=tuple)
    warn_count: int = 0
    critical_count: int = 0


class PortfolioRebalanceService:
    """リバランス計算サービス."""

    def __init__(self, portfolio_service=None):
        # 既存PortfolioServiceに依存（依存注入はテスト時のみ）
        if portfolio_service is None:
            from src.services.portfolio_service import PortfolioService
            portfolio_service = PortfolioService()
        self.portfolio_service = portfolio_service

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

        # 既存サービスからデータ取得（API経由・分割調整済み）
        holdings = self.portfolio_service.get_holdings(user_id)
        summary = self.portfolio_service.get_portfolio_summary(user_id)

        total_asset = float(summary.get("total_asset") or 0.0)
        current_cash = float(summary.get("cash_balance") or 0.0)
        daily_pnl_pct = summary.get("daily_change_total_asset_percent")
        # daily_pnl_pct は None or float

        # 銘柄別 holdings 辞書化
        holdings_by_code: Dict[str, Dict] = {h["etf_code"]: h for h in holdings}

        # 目標金額
        target_cash = total_asset * (TARGET_ALLOCATION["CASH"] / 100.0)
        cash_actual_pct = (
            (current_cash / total_asset * 100.0) if total_asset > 0 else 0.0
        )
        cash_deviation_pp = cash_actual_pct - TARGET_ALLOCATION["CASH"]

        sell_actions: List[RebalanceAction] = []
        buy_actions: List[RebalanceAction] = []
        # 採用銘柄の買付候補（予算スケーリング前）
        buy_candidates: List[Dict[str, float]] = []
        snapshots: List[HoldingSnapshot] = []
        deviations: Dict[str, float] = {}

        # --- 採用8銘柄の処理 ---
        adopted_codes = [c for c in TARGET_ALLOCATION.keys() if c != "CASH"]
        for code in adopted_codes:
            target_pct = TARGET_ALLOCATION[code]
            target_amount = total_asset * (target_pct / 100.0)

            h = holdings_by_code.get(code)
            if h is None:
                # 未保有 → 全額買付推奨
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
            # 株数化（floor: 単元未満は次回繰越）
            if current_price > 0 and abs(diff_amount) >= current_price:
                qty = int(math.floor(abs(diff_amount) / current_price))
                trade_amount = qty * current_price
                if diff_amount > 0 and qty > 0:
                    # 買付候補（あとで cash_budget で比例縮小する）
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
                    # 売却推奨
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
                    name=ETF_DISPLAY_NAMES.get(code, code),
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
        for code, h in holdings_by_code.items():
            if code in TARGET_ALLOCATION:
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
            # 採用外なので「目標=0」「乖離=actual_pct」
            target_pct = 0.0
            drift_pp = actual_pct
            deviations[code] = drift_pp

            # 株数（小数→四捨五入: 分割調整後の端数を呑み込んで全量売却に揃える）
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

            # 銘柄表示名は holdings 内 etf 情報優先
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
                    classification="CRITICAL",  # 採用外は常に要対応
                    is_adopted=False,
                )
            )

        # --- 買付予算制約: リスク資産買付総額 ≤ 現金 + 売却額 - 目標現金 ---
        # 採用外売却＋採用銘柄売却で発生する現金、初期現金、目標現金から
        # 実際に買付に回せる予算を計算し、超過する場合は比例縮小する。
        sum_sell_amount = sum(a.amount for a in sell_actions)
        cash_budget = current_cash + sum_sell_amount - target_cash
        sum_buy_amount_raw = sum(c["amount"] for c in buy_candidates)

        if sum_buy_amount_raw > cash_budget and sum_buy_amount_raw > 0:
            ratio = max(0.0, cash_budget / sum_buy_amount_raw) if sum_buy_amount_raw > 0 else 0.0
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
            # 予算内なので原案どおり登録
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
        target_weights: Dict[str, float] = {
            k: v for k, v in TARGET_ALLOCATION.items() if k != "CASH"
        }
        _adopted_sum = sum(target_weights.values()) + TARGET_ALLOCATION["CASH"]
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
        warn_count = sum(
            1 for s in snapshots if s.classification == "WARN"
        )
        critical_count = sum(
            1 for s in snapshots if s.classification == "CRITICAL"
        )
        if abs(cash_deviation_pp) >= DRIFT_WARN_PP:
            critical_count += 1
        elif abs(cash_deviation_pp) >= DRIFT_OK_PP:
            warn_count += 1

        return RebalancePlan(
            target_weights=target_weights,
            current_weights=current_weights,
            deviations=deviations,
            sell_actions=tuple(sell_actions),
            buy_actions=tuple(buy_actions),
            total_asset=total_asset,
            target_cash=target_cash,
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
    @staticmethod
    def _classify_drift(deviation_pp: float) -> str:
        """個別銘柄の乖離 → 分類."""
        abs_dev = abs(deviation_pp)
        if abs_dev < DRIFT_OK_PP:
            return "OK"
        if abs_dev < DRIFT_WARN_PP:
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
            if d.weekday() >= 5:  # 土日
                return False
            if jpholiday is not None and jpholiday.is_holiday(d):
                return False
            return True

        def last_business_day_of_month(year: int, month: int) -> date:
            # その月の末日を求める
            if month == 12:
                first_next = date(year + 1, 1, 1)
            else:
                first_next = date(year, month + 1, 1)
            d = first_next - timedelta(days=1)
            while not is_business_day(d):
                d -= timedelta(days=1)
            return d

        # 探索: 今年の3/6/9/12月末 → 来年の3月末まで
        quarter_months = [3, 6, 9, 12]
        candidates: List[date] = []
        for m in quarter_months:
            candidates.append(last_business_day_of_month(today.year, m))
        candidates.append(last_business_day_of_month(today.year + 1, 3))

        # 今日以降の最初の四半期末営業日
        for c in candidates:
            if c >= today:
                return c
        # 万一見つからなければ、来年3月末（fallback）
        return candidates[-1]
