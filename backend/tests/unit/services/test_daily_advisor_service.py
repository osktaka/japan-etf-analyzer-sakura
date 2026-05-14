"""Tests for DailyAdvisorService (boundary-focused)."""
from __future__ import annotations

from datetime import date

import pytest

from src.services.daily_advisor_service import (
    AllocationDrift,
    _check_allocation_drift,
    _check_loss_cut,
    _check_min_holding_period,
    _check_n225_drawdown,
    _check_take_profit,
    build_alert_context,
    build_evening_context,
    build_morning_context,
    build_weekly_context,
    classify_buckets,
    compute_alpha_vs_benchmark,
    compute_allocation_drift,
    compute_return_from_history,
    evaluate_mechanical_rules,
    is_weekly_review_day,
    make_fingerprint,
)
from src.services.strategy_loader import StrategyLoader

VALID = """---
revision: 2026-05-14
owner: test
benchmark: ^N225
review_frequency: weekly_friday
target_buckets:
  group_a: { label_ja: "A群（コア・逆相関）", weight_pct: 45.00 }
  group_b: { label_ja: "B群（日本株テーマ）", weight_pct: 45.00 }
  cash:    { label_ja: "現金",              weight_pct: 10.00 }
target_holdings:
  - { code: "2559", name: "オルカン",       bucket: "group_a", weight_pct: 15.00 }
  - { code: "1540", name: "純金",           bucket: "group_a", weight_pct: 15.00 }
  - { code: "200A", name: "半導体",         bucket: "group_a", weight_pct: 15.00 }
  - { code: "1306", name: "TOPIX",          bucket: "group_b", weight_pct:  9.00 }
  - { code: "1629", name: "商社",           bucket: "group_b", weight_pct:  9.00 }
  - { code: "1615", name: "銀行",           bucket: "group_b", weight_pct:  9.00 }
  - { code: "2646", name: "メタル",         bucket: "group_b", weight_pct:  9.00 }
  - { code: "1618", name: "エネルギー資源", bucket: "group_b", weight_pct:  9.00 }
mechanical_rules:
  min_holding_months: 6
  loss_cut_pct: -20.0
  take_profit_pct: [50.0, 100.0]
  n225_drawdown_trigger_pct: -5.0
  n225_drawdown_basis: previous_close
  n225_dca_lookback_days: 10
  alpha_deviation_threshold_pp: 10.0
  drift_ok_pp: 3.0
  drift_warn_pp: 5.0
  rebalance_check_basis: close
---
本文"""


@pytest.fixture
def strategy():
    return StrategyLoader.loads(VALID)


# ============================================================
# Date predicates
# ============================================================


class TestDatePredicates:
    def test_is_weekly_review_day_friday(self):
        assert is_weekly_review_day(date(2026, 5, 1)) is True  # 金曜

    def test_is_weekly_review_day_thursday(self):
        assert is_weekly_review_day(date(2026, 4, 30)) is False  # 木曜


# ============================================================
# Loss cut boundary
# ============================================================


class TestLossCut:
    def _holding(self, pnl_pct, days=200):
        return {
            "etf_code": "1306",
            "unrealized_pnl_percent": pnl_pct,
            "holding_days": days,
        }

    def test_just_under_threshold_does_not_fire(self):
        """-19.99% は発火しない."""
        h = self._holding(-19.99)
        r = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        assert r is None

    def test_exactly_at_threshold_fires(self):
        """-20.0% で発火する (>= 境界)."""
        h = self._holding(-20.0)
        r = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        assert r is not None
        assert r.rule_kind == "loss_cut"
        assert r.severity == "critical"

    def test_below_threshold_fires(self):
        """-20.01% で発火."""
        h = self._holding(-20.01)
        r = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        assert r is not None

    def test_min_holding_blocks_under_6_months(self):
        """6ヶ月未満は損切りブロック (5.99ヶ月相当)."""
        # 6 * 30 = 180 days; 5.99ヶ月 ≈ 179日
        h = self._holding(-25.0, days=179)
        r = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        assert r is None

    def test_min_holding_at_6_months_passes(self):
        """6ヶ月ちょうど (180日) で許可される."""
        h = self._holding(-25.0, days=180)
        r = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        assert r is not None

    def test_none_pnl_returns_none(self):
        h = {"etf_code": "1306", "unrealized_pnl_percent": None, "holding_days": 200}
        r = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date.today(), user_id="test",
        )
        assert r is None


# ============================================================
# Take profit boundary
# ============================================================


class TestTakeProfit:
    def _holding(self, pnl_pct):
        return {
            "etf_code": "2559",
            "unrealized_pnl_percent": pnl_pct,
            "holding_days": 100,
        }

    def test_just_under_50_does_not_fire(self):
        rs = _check_take_profit(
            self._holding(49.99),
            thresholds_pct=(50.0, 100.0),
            today=date.today(), user_id="test",
        )
        assert len(rs) == 0

    def test_exactly_50_fires_first_only(self):
        rs = _check_take_profit(
            self._holding(50.0),
            thresholds_pct=(50.0, 100.0),
            today=date.today(), user_id="test",
        )
        assert len(rs) == 1
        assert rs[0].rule_kind == "take_profit_1"

    def test_exactly_100_fires_both(self):
        rs = _check_take_profit(
            self._holding(100.0),
            thresholds_pct=(50.0, 100.0),
            today=date.today(), user_id="test",
        )
        assert len(rs) == 2
        kinds = {r.rule_kind for r in rs}
        assert kinds == {"take_profit_1", "take_profit_2"}


# ============================================================
# N225 drawdown boundary
# ============================================================


class TestN225Drawdown:
    def test_just_under_threshold_does_not_fire(self):
        r = _check_n225_drawdown(
            -4.99, threshold_pct=-5.0, today=date.today(), user_id="test"
        )
        assert r is None

    def test_exactly_at_threshold_fires(self):
        r = _check_n225_drawdown(
            -5.0, threshold_pct=-5.0, today=date.today(), user_id="test"
        )
        assert r is not None
        assert r.rule_kind == "n225_drawdown"
        assert r.severity == "warn"

    def test_below_threshold_fires(self):
        r = _check_n225_drawdown(
            -6.0, threshold_pct=-5.0, today=date.today(), user_id="test"
        )
        assert r is not None

    def test_none_returns_none(self):
        r = _check_n225_drawdown(
            None, threshold_pct=-5.0, today=date.today(), user_id="test"
        )
        assert r is None


# ============================================================
# Min holding period
# ============================================================


class TestMinHoldingPeriod:
    def test_5_99_months_blocks(self):
        h = {"holding_days": 179}  # < 180
        assert _check_min_holding_period(h, min_holding_months=6) is False

    def test_6_months_passes(self):
        h = {"holding_days": 180}
        assert _check_min_holding_period(h, min_holding_months=6) is True


# ============================================================
# Allocation drift
# ============================================================


class TestAllocationDrift:
    def test_compute_drift(self, strategy):
        # group_a target=0.45, group_b target=0.45, cash target=0.10
        actual = {"group_a": 0.30, "group_b": 0.45, "cash": 0.25, "other": 0.0}
        drifts = compute_allocation_drift(
            strategy=strategy, actual_buckets=actual
        )
        d_map = {d.bucket: d for d in drifts}
        assert d_map["group_a"].drift_pp == -15.0
        assert d_map["group_b"].drift_pp == 0.0
        assert d_map["cash"].drift_pp == 15.0
        # other は actual=0 のため drift エントリは生成されない
        assert "other" not in d_map

    def test_compute_drift_with_other(self, strategy):
        """採用外保有がある場合、other バケットが drift に出る."""
        actual = {"group_a": 0.40, "group_b": 0.40, "cash": 0.10, "other": 0.10}
        drifts = compute_allocation_drift(
            strategy=strategy, actual_buckets=actual
        )
        d_map = {d.bucket: d for d in drifts}
        assert "other" in d_map
        assert d_map["other"].target_pct == 0.0
        assert d_map["other"].actual_pct == 10.0
        assert d_map["other"].drift_pp == 10.0

    def test_compute_drift_warn_threshold_propagates(self, strategy):
        actual = {"group_a": 0.45, "group_b": 0.45, "cash": 0.10}
        drifts = compute_allocation_drift(
            strategy=strategy, actual_buckets=actual
        )
        for d in drifts:
            assert d.warn_threshold_pp == 5.0

    def test_check_drift_warn_above_threshold(self):
        drifts = (
            AllocationDrift(
                bucket="group_a", target_pct=45.0, actual_pct=38.0,
                drift_pp=-7.0, warn_threshold_pp=5.0,
            ),
        )
        rs = _check_allocation_drift(
            drifts, threshold_pct=5.0, today=date.today(), user_id="test"
        )
        assert len(rs) == 1
        assert rs[0].severity == "warn"

    def test_check_drift_under_threshold(self):
        drifts = (
            AllocationDrift(
                bucket="group_a", target_pct=45.0, actual_pct=42.0,
                drift_pp=-3.0, warn_threshold_pp=5.0,
            ),
        )
        rs = _check_allocation_drift(
            drifts, threshold_pct=5.0, today=date.today(), user_id="test"
        )
        assert len(rs) == 0


# ============================================================
# Fingerprint
# ============================================================


class TestFingerprint:
    def test_same_inputs_same_fingerprint(self):
        a = make_fingerprint(
            occurred_on=date(2026, 4, 29), rule_kind="loss_cut",
            code="1306", user_id="test",
        )
        b = make_fingerprint(
            occurred_on=date(2026, 4, 29), rule_kind="loss_cut",
            code="1306", user_id="test",
        )
        assert a == b

    def test_different_date_different_fingerprint(self):
        a = make_fingerprint(
            occurred_on=date(2026, 4, 29), rule_kind="loss_cut",
            code="1306", user_id="test",
        )
        b = make_fingerprint(
            occurred_on=date(2026, 4, 30), rule_kind="loss_cut",
            code="1306", user_id="test",
        )
        assert a != b

    def test_different_rule_different_fingerprint(self):
        a = make_fingerprint(
            occurred_on=date(2026, 4, 29), rule_kind="loss_cut",
            code="1306", user_id="test",
        )
        b = make_fingerprint(
            occurred_on=date(2026, 4, 29), rule_kind="take_profit_1",
            code="1306", user_id="test",
        )
        assert a != b

    def test_no_duplicate_for_same_day_same_holding_same_rule(self):
        """同日同銘柄同ルールで重複しない (発動2回 → fingerprint同一)."""
        h = {"etf_code": "1306", "unrealized_pnl_percent": -25.0, "holding_days": 200}
        r1 = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        r2 = _check_loss_cut(
            h, threshold_pct=-20.0, min_holding_months=6,
            today=date(2026, 4, 29), user_id="test",
        )
        assert r1 is not None and r2 is not None
        assert r1.fingerprint == r2.fingerprint


# ============================================================
# Bucket classification
# ============================================================


class TestClassifyBuckets:
    def test_basic_classification(self, strategy):
        # group_a 採用銘柄: 2559/1540/200A, group_b 採用銘柄: 1306/1629/1615/2646/1618
        holdings = [
            {"etf_code": "2559", "current_value": 450_000.0},  # group_a
            {"etf_code": "1306", "current_value": 450_000.0},  # group_b
        ]
        b = classify_buckets(
            holdings=holdings, cash_balance=100_000.0, strategy=strategy
        )
        assert round(b["group_a"], 2) == 0.45
        assert round(b["group_b"], 2) == 0.45
        assert round(b["cash"], 2) == 0.10
        assert b["other"] == 0.0

    def test_other_bucket_for_unlisted_codes(self, strategy):
        """採用外銘柄は other バケットに分類される."""
        holdings = [
            {"etf_code": "2559", "current_value": 400_000.0},  # group_a
            {"etf_code": "1306", "current_value": 400_000.0},  # group_b
            {"etf_code": "9999", "current_value": 100_000.0},  # 採用外 → other
        ]
        b = classify_buckets(
            holdings=holdings, cash_balance=100_000.0, strategy=strategy
        )
        assert round(b["other"], 2) == 0.10
        assert round(b["group_a"], 2) == 0.40
        assert round(b["group_b"], 2) == 0.40
        assert round(b["cash"], 2) == 0.10

    def test_empty_returns_zeros(self, strategy):
        b = classify_buckets(holdings=[], cash_balance=0.0, strategy=strategy)
        assert b["group_a"] == 0.0
        assert b["group_b"] == 0.0
        assert b["cash"] == 0.0
        assert b["other"] == 0.0


# ============================================================
# Alpha vs benchmark
# ============================================================


class TestAlpha:
    def test_compute_alpha(self):
        a = compute_alpha_vs_benchmark(
            portfolio_return_pct=8.0, benchmark_return_pct=10.0
        )
        assert a == -2.0

    def test_compute_alpha_none(self):
        assert (
            compute_alpha_vs_benchmark(
                portfolio_return_pct=None, benchmark_return_pct=10.0
            )
            is None
        )


# ============================================================
# compute_return_from_history
# ============================================================


class TestReturnFromHistory:
    def test_5day_return(self):
        # 6件 = 基準 + 5営業日
        history = [
            {"value": 1000.0},
            {"value": 1010.0},
            {"value": 1020.0},
            {"value": 1030.0},
            {"value": 1040.0},
            {"value": 1050.0},
        ]
        # (1050 - 1000) / 1000 * 100 = 5.0%
        assert compute_return_from_history(history, lookback_days=5) == 5.0

    def test_negative_return(self):
        history = [
            {"value": 1000.0},
            {"value": 990.0},
            {"value": 980.0},
            {"value": 970.0},
            {"value": 960.0},
            {"value": 950.0},
        ]
        assert compute_return_from_history(history, lookback_days=5) == -5.0

    def test_insufficient_data_returns_none(self):
        history = [{"value": 1000.0}, {"value": 1010.0}]
        assert compute_return_from_history(history, lookback_days=5) is None

    def test_empty_returns_none(self):
        assert compute_return_from_history([], lookback_days=5) is None

    def test_zero_base_returns_none(self):
        history = [{"value": 0.0}] + [{"value": 100.0}] * 5
        assert compute_return_from_history(history, lookback_days=5) is None

    def test_custom_value_key(self):
        history = [{"total_asset": 1000.0}, {"total_asset": 1100.0}]
        # 1営業日リターン: 10.0%
        assert (
            compute_return_from_history(
                history, lookback_days=1, value_key="total_asset"
            )
            == 10.0
        )

    def test_missing_value_key_returns_none(self):
        history = [{"value": None}] + [{"value": 100.0}] * 5
        assert compute_return_from_history(history, lookback_days=5) is None


# ============================================================
# Aggregator: evaluate_mechanical_rules
# ============================================================


class TestEvaluateRules:
    def test_no_triggers(self, strategy):
        holdings = [
            {"etf_code": "2559", "unrealized_pnl_percent": 5.0, "holding_days": 200,
             "current_value": 650_000.0},
        ]
        triggers = evaluate_mechanical_rules(
            strategy=strategy,
            holdings=holdings,
            n225_change_pct=-1.0,
            allocation_drifts=(),
            today=date(2026, 4, 29),
            user_id="test",
        )
        assert len(triggers) == 0

    def test_loss_cut_and_n225_drawdown(self, strategy):
        holdings = [
            {"etf_code": "2559", "unrealized_pnl_percent": -25.0, "holding_days": 200,
             "current_value": 500_000.0},
        ]
        triggers = evaluate_mechanical_rules(
            strategy=strategy,
            holdings=holdings,
            n225_change_pct=-7.0,
            allocation_drifts=(),
            today=date(2026, 4, 29),
            user_id="test",
        )
        kinds = {t.rule_kind for t in triggers}
        assert "loss_cut" in kinds
        assert "n225_drawdown" in kinds


# ============================================================
# Context builders
# ============================================================


class TestContextBuilders:
    def test_morning_context(self, strategy):
        ctx = build_morning_context(
            strategy=strategy,
            today=date(2026, 5, 7),
            user_id="test",
            summary={
                "total_asset": 1_000_000.0,
                "total_value": 900_000.0,
                "cash_balance": 100_000.0,
                "daily_change_total_asset_percent": 0.5,
                "holdings_count": 6,
            },
        )
        assert ctx.kind == "morning"
        # 旧 sells_today/buys_today フィールドは NotificationContext から撤去済み.
        # 本日の発注情報はテンプレ側で rebalance_plan から導出する.
        assert ctx.daily_change_pct == 0.5
        # rebalance_plan 未指定時は None (rebalance_plan は morning kind 専用フィールド).
        assert ctx.rebalance_plan is None
        # 配分閾値が strategy から正しく注入されている
        assert ctx.drift_ok_pp == strategy.mechanical_rules.drift_ok_pp
        assert ctx.drift_warn_pp == strategy.mechanical_rules.drift_warn_pp

    def test_evening_context(self, strategy):
        drifts = (
            AllocationDrift(
                bucket="group_a", target_pct=45.0, actual_pct=43.0,
                drift_pp=-2.0, warn_threshold_pp=5.0,
            ),
        )
        ctx = build_evening_context(
            strategy=strategy,
            today=date(2026, 4, 29),
            user_id="test",
            summary={
                "total_asset": 1_000_000.0, "total_value": 900_000.0,
                "cash_balance": 100_000.0, "holdings_count": 6,
                "daily_change_total_asset_percent": -0.3,
            },
            drifts=drifts,
            triggers=(),
        )
        assert ctx.kind == "evening"
        # warn_threshold_pp が strategy 由来で揃えられている
        assert all(
            d.warn_threshold_pp == strategy.mechanical_rules.drift_warn_pp
            for d in ctx.allocation_drifts
        )
        # 内容は変わらない
        assert ctx.allocation_drifts[0].bucket == "group_a"
        assert ctx.allocation_drifts[0].drift_pp == -2.0

    def test_weekly_context_alpha(self, strategy):
        ctx = build_weekly_context(
            strategy=strategy,
            today=date(2026, 5, 1),
            user_id="test",
            summary={"total_asset": 1_000_000.0, "total_value": 900_000.0,
                     "cash_balance": 100_000.0, "holdings_count": 6},
            drifts=(),
            triggers=(),
            portfolio_return_pct=2.0,
            benchmark_return_pct=3.0,
        )
        assert ctx.alpha_pp == -1.0

    def test_alert_context(self, strategy):
        from src.services.daily_advisor_service import RuleTrigger

        triggers = (
            RuleTrigger(
                rule_kind="n225_drawdown", code=None, severity="warn",
                message="N225 -6%", fingerprint="abc",
            ),
        )
        ctx = build_alert_context(
            strategy=strategy,
            today=date(2026, 4, 29),
            user_id="test",
            triggers=triggers,
        )
        assert ctx.kind == "alert"
        assert len(ctx.triggers) == 1
