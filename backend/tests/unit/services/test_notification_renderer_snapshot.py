"""NotificationRenderer のスナップショットテスト.

新仕様（アナリスト視点・モバイル最適化リライト）の出力を `__snapshots__/`
ディレクトリ配下のゴールデンファイルと完全一致比較する。回帰防止用。

期待値を更新したい場合:
    docker compose exec -T -e SNAPSHOT_UPDATE=1 backend \\
        pytest tests/unit/services/test_notification_renderer_snapshot.py -v

テンプレート/レンダラ変更後は出力差分を目視確認した上で
SNAPSHOT_UPDATE=1 で更新し、Git で差分をレビューしてからコミットすること。

外部ライブラリ（syrupy 等）は不採用＝YAGNI。手書きの一致比較で十分。

ケース定義は `backend/scripts/_dev/dump_email_artifacts.py` の `_build_cases()`
と等価。両者の重複は許容（fixture 共有のためにモジュールを切り出すと
依存方向が複雑化するため）。
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest

from src.services.daily_advisor_service import (
    AllocationDrift,
    NotificationContext,
    RuleTrigger,
)
from src.services.notification_renderer import NotificationRenderer

SNAPSHOT_DIR = Path(__file__).parent / "__snapshots__"


# ---------------------------------------------------------------------------
# スナップショット比較ヘルパ
# ---------------------------------------------------------------------------
def assert_snapshot(name: str, actual: str) -> None:
    """`__snapshots__/{name}` と actual を比較.

    SNAPSHOT_UPDATE=1 の場合は期待値ファイルを上書き保存して PASS とする。
    期待値ファイルが存在しない場合は明示的に失敗（誤検出防止）。
    """
    expected_file = SNAPSHOT_DIR / name
    if os.environ.get("SNAPSHOT_UPDATE"):
        expected_file.parent.mkdir(parents=True, exist_ok=True)
        expected_file.write_text(actual, encoding="utf-8")
        return
    if not expected_file.exists():
        raise AssertionError(
            f"Snapshot missing: {expected_file}. "
            "Run with SNAPSHOT_UPDATE=1 to create."
        )
    expected = expected_file.read_text(encoding="utf-8")
    assert actual == expected, (
        f"Snapshot mismatch for {name}. "
        f"Run with SNAPSHOT_UPDATE=1 to update if change is intentional."
    )


# ---------------------------------------------------------------------------
# fixture builder
# dump_email_artifacts.py と等価（CLAUDE.md コメント参照）
# ---------------------------------------------------------------------------
def _morning_ctx(**overrides) -> NotificationContext:
    base = dict(
        kind="morning",
        today=date(2026, 5, 7),
        user_id="test",
        strategy_revision=date(2026, 4, 29),
        benchmark="^N225",
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
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
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        daily_change_pct=-0.3,
        holdings_count=6,
        allocation_drifts=(
            AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=43.0, drift_pp=-2.0, warn_threshold_pp=5.0),
            AllocationDrift(bucket="group_b", target_pct=45.0, actual_pct=47.0, drift_pp=2.0, warn_threshold_pp=5.0),
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
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        total_asset=1_000_000.0,
        total_value=900_000.0,
        cash_balance=100_000.0,
        holdings_count=6,
        allocation_drifts=(
            AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=40.0, drift_pp=-5.0, warn_threshold_pp=5.0),
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
        drift_ok_pp=3.0,
        drift_warn_pp=5.0,
        triggers=(
            RuleTrigger(
                rule_kind="n225_drawdown",
                code=None,
                severity="warn",
                message="N225 急落 -6%",
                fingerprint="abc",
                payload={"change_pct": -6.0, "threshold_pct": -5.0},
            ),
        ),
    )
    base.update(overrides)
    return NotificationContext(**base)


# ---------------------------------------------------------------------------
# 11ケース × md/html を検証
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def renderer() -> NotificationRenderer:
    return NotificationRenderer()


def _check(renderer: NotificationRenderer, kind_tag: str, ctx: NotificationContext) -> None:
    md, html = renderer.render(ctx)
    assert_snapshot(f"{kind_tag}.md", md)
    assert_snapshot(f"{kind_tag}.html", html)


# ---- morning: 2ケース ----
# 旧 sells_today/buys_today を使った action_buy_only/action_sell_buy ケースは撤去
# （sells_today/buys_today フィールドは NotificationContext から削除済み）
def test_snapshot_morning_seikan(renderer):
    ctx = _morning_ctx(triggers=())
    _check(renderer, "morning_seikan", ctx)


def test_snapshot_morning_critical(renderer):
    ctx = _morning_ctx(
        triggers=(
            RuleTrigger(
                rule_kind="loss_cut",
                code="1306",
                severity="critical",
                message="loss cut 発動",
                fingerprint="f-critical",
            ),
        ),
    )
    _check(renderer, "morning_critical", ctx)


# ---- evening: 2ケース ----
def test_snapshot_evening_seikan(renderer):
    _check(renderer, "evening_seikan", _evening_ctx())


def test_snapshot_evening_warn_drift(renderer):
    ctx = _evening_ctx(
        allocation_drifts=(
            AllocationDrift(bucket="group_a", target_pct=45.0, actual_pct=35.0, drift_pp=-10.0, warn_threshold_pp=5.0),
        ),
        triggers=(
            RuleTrigger(
                rule_kind="allocation_drift",
                code=None,
                severity="warn",
                message="配分逸脱: group_a",
                fingerprint="f-drift",
            ),
        ),
    )
    _check(renderer, "evening_warn_drift", ctx)


# ---- weekly: 2ケース ----
def test_snapshot_weekly_seikan(renderer):
    _check(renderer, "weekly_seikan", _weekly_ctx())


def test_snapshot_weekly_warn_alpha(renderer):
    _check(renderer, "weekly_warn_alpha", _weekly_ctx(alpha_pp=-3.0))


# ---- alert: 3ケース ----
def test_snapshot_alert_critical(renderer):
    ctx = _alert_ctx(triggers=(
        RuleTrigger(
            rule_kind="loss_cut",
            code="1306",
            severity="critical",
            message="loss cut 発動",
            fingerprint="f-alert-critical",
        ),
    ))
    _check(renderer, "alert_critical", ctx)


def test_snapshot_alert_warn(renderer):
    _check(renderer, "alert_warn", _alert_ctx())


def test_snapshot_alert_info(renderer):
    ctx = _alert_ctx(triggers=(
        RuleTrigger(
            rule_kind="n225_drawdown",
            code=None,
            severity="info",
            message="情報通知",
            fingerprint="f-alert-info",
        ),
    ))
    _check(renderer, "alert_info", ctx)
