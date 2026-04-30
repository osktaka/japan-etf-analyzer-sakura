"""Tests for NotificationRenderer."""
from __future__ import annotations

from datetime import date

import pytest

from src.services.daily_advisor_service import (
    AllocationDrift,
    BuyAction,
    NotificationContext,
    RuleTrigger,
    SellAction,
)
from src.services.notification_renderer import NotificationRenderer


@pytest.fixture
def renderer():
    return NotificationRenderer()


def _morning_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="morning",
        today=date(2026, 5, 7),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        sells_today=(SellAction(code="1540", name="純金", quantity=10, action="all", reason="金過剰"),),
        buys_today=(BuyAction(code="2559", quantity=3),),
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        daily_change_pct=0.5,
        holdings_count=6,
    )
    base.update(overrides)
    return NotificationContext(**base)


def _evening_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="evening",
        today=date(2026, 4, 29),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        daily_change_pct=-0.3,
        holdings_count=6,
        allocation_drifts=(
            AllocationDrift(bucket="core", target_pct=65.0, actual_pct=63.0, drift_pp=-2.0),
            AllocationDrift(bucket="theme", target_pct=25.0, actual_pct=27.0, drift_pp=2.0),
        ),
        triggers=(),
    )
    base.update(overrides)
    return NotificationContext(**base)


def _weekly_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="weekly",
        today=date(2026, 5, 1),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        holdings_count=6,
        allocation_drifts=(
            AllocationDrift(bucket="core", target_pct=65.0, actual_pct=60.0, drift_pp=-5.0),
        ),
        triggers=(),
        alpha_pp=-1.0,
        period_label="過去5営業日",
        portfolio_return_pct=2.0,
        benchmark_return_pct=3.0,
    )
    base.update(overrides)
    return NotificationContext(**base)


def _alert_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="alert",
        today=date(2026, 4, 29),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        triggers=(
            RuleTrigger(
                rule_kind="n225_drawdown", code=None, severity="warn",
                message="N225 急落 -6%", fingerprint="abc",
                payload={"change_pct": -6.0, "threshold_pct": -5.0},
            ),
        ),
    )
    base.update(overrides)
    return NotificationContext(**base)


class TestRender:
    def test_morning(self, renderer):
        md, html = renderer.render(_morning_ctx())
        assert "朝のタスク" in md
        assert "1540 純金" in md
        assert "2559" in md
        assert "前日比: +0.50%" in md
        assert "<h1>" in html
        assert "1,000,000" in md
        # リード文・タグ
        assert "**要対応**" in md
        assert "今日の発注" in md

    def test_evening(self, renderer):
        md, html = renderer.render(_evening_ctx())
        assert "夕方のレビュー" in md
        assert "core" in md
        assert "theme" in md
        assert "<h1>" in html
        # リード文
        assert "本日 -0.30%" in md
        assert "**静観**" in md

    def test_weekly_with_alpha(self, renderer):
        md, html = renderer.render(_weekly_ctx())
        assert "週次レビュー" in md
        assert "α" in md
        assert "-1.00pp" in md
        assert "過去5営業日" in md
        # 推奨アクション (drift_pp = -5.0 は abs >5 でないが、α<=-2.0 でもないため、推奨セクション無し)
        # → ここは静観 or 要確認 に応じた追加検証は別テスト
        assert "**静観**" in md

    def test_weekly_with_negative_alpha_recommends_action(self, renderer):
        # α=-3.0 で α<=-2 → 推奨アクションセクション出る
        ctx = _weekly_ctx(alpha_pp=-3.0)
        md, _ = renderer.render(ctx)
        assert "来週の推奨アクション" in md
        assert "core ETFの追加買付" in md
        assert "**要確認**" in md

    def test_alert(self, renderer):
        md, html = renderer.render(_alert_ctx())
        assert "機械ルール" in md
        assert "n225_drawdown" in md
        assert "N225 急落" in md
        assert "<h1" in html
        # 推奨アクション
        assert "推奨アクション" in md
        assert "静観 or 戦略書の急落時方針" in md


class TestSubject:
    def test_morning_subject(self, renderer):
        s = renderer.subject_for(_morning_ctx())
        assert "[ETF朝/要対応]" in s
        assert "2026-05-07" in s
        assert "test" in s

    def test_morning_subject_quiet(self, renderer):
        # 売買予定なし → 静観
        ctx = _morning_ctx(sells_today=(), buys_today=())
        s = renderer.subject_for(ctx)
        assert "[ETF朝/静観]" in s

    def test_evening_subject_quiet(self, renderer):
        s = renderer.subject_for(_evening_ctx())
        assert "[ETF夕/静観]" in s

    def test_weekly_subject(self, renderer):
        # α=-1.0 (>-2.0) → 静観
        s = renderer.subject_for(_weekly_ctx())
        assert "[ETF週次/静観]" in s

    def test_alert_critical_subject(self, renderer):
        ctx = NotificationContext(
            kind="alert",
            today=date(2026, 4, 29),
            user_id="test",
            strategy_revision=date(2026, 4, 29),
            benchmark="^N225",
            triggers=(
                RuleTrigger(
                    rule_kind="loss_cut", code="1306", severity="critical",
                    message="loss cut", fingerprint="x",
                ),
            ),
        )
        s = renderer.subject_for(ctx)
        assert "緊急" in s
        assert "[ETF/緊急]" in s

    def test_alert_warn_subject(self, renderer):
        s = renderer.subject_for(_alert_ctx())
        assert "[ETF/要確認]" in s


class TestUrgencyTag:
    def test_critical_in_morning(self, renderer):
        ctx = _morning_ctx(triggers=(
            RuleTrigger(
                rule_kind="loss_cut", code="1306", severity="critical",
                message="x", fingerprint="f1",
            ),
        ))
        assert renderer.urgency_tag(ctx) == "緊急"

    def test_morning_with_action(self, renderer):
        # sells/buys あり、critical なし → 要対応
        assert renderer.urgency_tag(_morning_ctx()) == "要対応"

    def test_warn_in_evening(self, renderer):
        ctx = _evening_ctx(triggers=(
            RuleTrigger(
                rule_kind="allocation_drift", code=None, severity="warn",
                message="drift", fingerprint="f2",
            ),
        ))
        assert renderer.urgency_tag(ctx) == "要確認"

    def test_weekly_alpha_loss(self, renderer):
        ctx = _weekly_ctx(alpha_pp=-3.0)
        assert renderer.urgency_tag(ctx) == "要確認"

    def test_quiet(self, renderer):
        ctx = _morning_ctx(sells_today=(), buys_today=(), triggers=())
        assert renderer.urgency_tag(ctx) == "静観"

    def test_alert_info(self, renderer):
        ctx = _alert_ctx(triggers=(
            RuleTrigger(
                rule_kind="n225_drawdown", code=None, severity="info",
                message="x", fingerprint="f3",
            ),
        ))
        assert renderer.urgency_tag(ctx) == "情報"


class TestSummary:
    def test_morning_critical(self, renderer):
        ctx = _morning_ctx(triggers=(
            RuleTrigger(
                rule_kind="loss_cut", code="1306", severity="critical",
                message="x", fingerprint="f1",
            ),
        ))
        s = renderer.summary_for(ctx)
        assert "緊急" in s
        assert "loss_cut" in s

    def test_morning_with_action_both(self, renderer):
        # sells=1, buys=1
        s = renderer.summary_for(_morning_ctx())
        assert "売却1件" in s
        assert "買付1件" in s

    def test_morning_buy_only(self, renderer):
        ctx = _morning_ctx(sells_today=(), buys_today=(BuyAction(code="2559", quantity=3),))
        s = renderer.summary_for(ctx)
        assert "買付1件のDCA" in s

    def test_morning_quiet(self, renderer):
        ctx = _morning_ctx(sells_today=(), buys_today=())
        s = renderer.summary_for(ctx)
        assert "発注予定なし" in s
        assert "静観" in s

    def test_morning_no_double_count_allocation_drift(self, renderer):
        # allocation_drift trigger と is_warn drift のダブルカウント防止
        ctx = _morning_ctx(
            sells_today=(),
            buys_today=(),
            allocation_drifts=(
                AllocationDrift(bucket="core", target_pct=65.0, actual_pct=55.0, drift_pp=-10.0),
            ),
            triggers=(
                RuleTrigger(
                    rule_kind="allocation_drift", code=None, severity="warn",
                    message="配分逸脱: core", fingerprint="a"
                ),
            ),
        )
        s = renderer.summary_for(ctx)
        assert "配分逸脱1件継続中" in s

    def test_evening_with_change(self, renderer):
        s = renderer.summary_for(_evening_ctx())
        assert "本日 -0.30%" in s
        assert "配分・ルール異常なし" in s

    def test_evening_with_warn(self, renderer):
        ctx = _evening_ctx(allocation_drifts=(
            AllocationDrift(bucket="core", target_pct=65.0, actual_pct=55.0, drift_pp=-10.0),
        ))
        s = renderer.summary_for(ctx)
        assert "本日 -0.30%" in s
        assert "配分逸脱1件あり" in s

    def test_evening_no_double_count(self, renderer):
        # allocation_drift trigger と is_warn drift を二重に数えないこと
        ctx = _evening_ctx(
            allocation_drifts=(
                AllocationDrift(bucket="core", target_pct=65.0, actual_pct=55.0, drift_pp=-10.0),
                AllocationDrift(bucket="theme", target_pct=25.0, actual_pct=10.0, drift_pp=-15.0),
            ),
            triggers=(
                RuleTrigger(rule_kind="allocation_drift", code=None, severity="warn",
                            message="配分逸脱: core", fingerprint="a"),
                RuleTrigger(rule_kind="allocation_drift", code=None, severity="warn",
                            message="配分逸脱: theme", fingerprint="b"),
            ),
        )
        s = renderer.summary_for(ctx)
        assert "配分逸脱2件" in s
        assert "ルール警告" not in s

    def test_evening_other_rule_warn(self, renderer):
        # allocation_drift 以外の warn は ルール警告として別カウント
        ctx = _evening_ctx(
            allocation_drifts=(
                AllocationDrift(bucket="core", target_pct=65.0, actual_pct=55.0, drift_pp=-10.0),
            ),
            triggers=(
                RuleTrigger(rule_kind="n225_drawdown", code=None, severity="warn",
                            message="N225 -6%", fingerprint="x"),
            ),
        )
        s = renderer.summary_for(ctx)
        assert "配分逸脱1件" in s
        assert "ルール警告1件" in s

    def test_weekly_negative_alpha(self, renderer):
        ctx = _weekly_ctx(alpha_pp=-3.0)
        s = renderer.summary_for(ctx)
        assert "α -3.00pp" in s
        assert "負け" in s

    def test_weekly_outperform(self, renderer):
        ctx = _weekly_ctx(alpha_pp=3.5)
        s = renderer.summary_for(ctx)
        assert "アウトパフォーム" in s

    def test_weekly_no_alpha(self, renderer):
        ctx = _weekly_ctx(alpha_pp=None, portfolio_return_pct=None, benchmark_return_pct=None)
        s = renderer.summary_for(ctx)
        assert "算出不可" in s

    def test_alert_warn(self, renderer):
        s = renderer.summary_for(_alert_ctx())
        assert "warnアラート1件" in s
        assert "n225_drawdown" in s

    def test_alert_many_triggers(self, renderer):
        triggers = tuple(
            RuleTrigger(
                rule_kind=f"loss_cut", code=str(1300 + i), severity="critical",
                message="m", fingerprint=f"f{i}",
            )
            for i in range(5)
        )
        ctx = _alert_ctx(triggers=triggers)
        s = renderer.summary_for(ctx)
        assert "criticalアラート5件" in s
        assert "他2件" in s


class TestRecommendedAction:
    def test_known_kinds(self, renderer):
        for kind, expect_substr in [
            ("loss_cut", "売却検討"),
            ("take_profit_1", "段階的売却（第1段）"),
            ("take_profit_2", "段階的売却（第2段）"),
            ("n225_drawdown", "戦略書の急落時方針"),
            ("allocation_drift", "配分是正"),
        ]:
            t = RuleTrigger(
                rule_kind=kind, code=None, severity="warn",
                message="x", fingerprint=f"f-{kind}",
            )
            assert expect_substr in renderer.recommended_action(t)

    def test_unknown_kind(self, renderer):
        t = RuleTrigger(
            rule_kind="unknown_rule_xxx", code=None, severity="info",
            message="x", fingerprint="f-unk",
        )
        assert renderer.recommended_action(t) == "戦略書を確認してください。"
