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


def _morning_ctx() -> NotificationContext:
    return NotificationContext(
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


def _evening_ctx() -> NotificationContext:
    return NotificationContext(
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


def _weekly_ctx() -> NotificationContext:
    return NotificationContext(
        kind="weekly",
        today=date(2026, 5, 1),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        total_asset=1_000_000.0, total_value=900_000.0, cash_balance=100_000.0,
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


def _alert_ctx() -> NotificationContext:
    return NotificationContext(
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


class TestRender:
    def test_morning(self, renderer):
        md, html = renderer.render(_morning_ctx())
        assert "朝のタスク" in md
        assert "1540 純金" in md
        assert "2559" in md
        assert "前日比: +0.50%" in md
        assert "<h1>" in html
        assert "1,000,000" in md

    def test_evening(self, renderer):
        md, html = renderer.render(_evening_ctx())
        assert "夕方のレビュー" in md
        assert "core" in md
        assert "theme" in md
        assert "<h1>" in html

    def test_weekly_with_alpha(self, renderer):
        md, html = renderer.render(_weekly_ctx())
        assert "週次レビュー" in md
        assert "α" in md
        assert "-1.00pp" in md
        assert "過去5営業日" in md

    def test_alert(self, renderer):
        md, html = renderer.render(_alert_ctx())
        assert "機械ルール" in md
        assert "n225_drawdown" in md
        assert "N225 急落" in md
        assert "<h1" in html


class TestSubject:
    def test_morning_subject(self, renderer):
        s = renderer.subject_for(_morning_ctx())
        assert "[ETF朝]" in s
        assert "2026-05-07" in s

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
        assert "critical" in s
