"""メール通知レンダラーの現状出力を artifact として保存する開発用スクリプト.

リライト前後のリグレッション基準（diff用）を作成するため、
NotificationRenderer.render(ctx) の出力を tmp/email_artifacts_before/ に書き出す.

使い方（開発環境）:
    # コンテナ内 /tmp/email_artifacts_before/ に生成されるため、
    # 実行後にホスト側 tmp/ ディレクトリへコピーする:
    docker compose exec -T backend python3 scripts/_dev/dump_email_artifacts.py
    docker cp japan-etf-analyzer-sakura-backend-1:/tmp/email_artifacts_before \\
        $(pwd)/tmp/

    # 出力先を上書きしたい場合:
    docker compose exec -T -e EMAIL_ARTIFACTS_DIR=/app/scripts/_dev/_out \\
        backend python3 scripts/_dev/dump_email_artifacts.py

既存コード（renderer/template/model）には一切手を入れない. read-only.

fixture は test_notification_renderer.py の _morning_ctx 等と同じ初期値を
複製している（pytest fixture はテストコンテキスト外で再利用できないため）.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

# プロジェクトルート特定 (backend/scripts/_dev/ → backend/scripts/ → backend/ → root)
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

from src.services.daily_advisor_models import (  # noqa: E402
    AllocationDrift,
    NotificationContext,
    RuleTrigger,
)
from src.services.notification_renderer import NotificationRenderer  # noqa: E402

_DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp" / "email_artifacts_before"
OUTPUT_DIR = Path(os.environ.get("EMAIL_ARTIFACTS_DIR") or _DEFAULT_OUTPUT_DIR)


# ---------------------------------------------------------------------------
# fixture builder（test_notification_renderer.py と等価）
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
# ダンプ対象ケース
# ---------------------------------------------------------------------------
def _build_cases() -> list[tuple[str, str, NotificationContext]]:
    """(kind, tag, ctx) のリストを返す.

    ファイル名は f'{kind}_{tag}.md|.html' となる.
    """
    cases: list[tuple[str, str, NotificationContext]] = []

    # ---- morning: 2ケース ----
    # 旧 sells_today/buys_today 経由のケースは撤去済み（model から削除）
    # 静観: 売買なし、トリガーなし
    cases.append((
        "morning",
        "seikan",
        _morning_ctx(triggers=()),
    ))
    # 緊急 (critical trigger)
    cases.append((
        "morning",
        "critical",
        _morning_ctx(
            triggers=(
                RuleTrigger(
                    rule_kind="loss_cut",
                    code="1306",
                    severity="critical",
                    message="loss cut 発動",
                    fingerprint="f-critical",
                ),
            ),
        ),
    ))

    # ---- evening: 2ケース ----
    # 静観: warn なし
    cases.append((
        "evening",
        "seikan",
        _evening_ctx(),
    ))
    # 要確認: warn 配分逸脱
    cases.append((
        "evening",
        "warn_drift",
        _evening_ctx(
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
        ),
    ))

    # ---- weekly: 2ケース ----
    # 静観: α=-1.0 (>-2.0)
    cases.append((
        "weekly",
        "seikan",
        _weekly_ctx(),
    ))
    # 要確認: α=-3.0 (<=-2.0)
    cases.append((
        "weekly",
        "warn_alpha",
        _weekly_ctx(alpha_pp=-3.0),
    ))

    # ---- alert: 3ケース ----
    cases.append((
        "alert",
        "critical",
        _alert_ctx(triggers=(
            RuleTrigger(
                rule_kind="loss_cut",
                code="1306",
                severity="critical",
                message="loss cut 発動",
                fingerprint="f-alert-critical",
            ),
        )),
    ))
    cases.append((
        "alert",
        "warn",
        _alert_ctx(),  # デフォルトは warn (n225_drawdown)
    ))
    cases.append((
        "alert",
        "info",
        _alert_ctx(triggers=(
            RuleTrigger(
                rule_kind="n225_drawdown",
                code=None,
                severity="info",
                message="情報通知",
                fingerprint="f-alert-info",
            ),
        )),
    ))

    return cases


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    renderer = NotificationRenderer()

    cases = _build_cases()
    written: list[str] = []
    for kind, tag, ctx in cases:
        md, html = renderer.render(ctx)
        md_path = OUTPUT_DIR / f"{kind}_{tag}.md"
        html_path = OUTPUT_DIR / f"{kind}_{tag}.html"
        md_path.write_text(md, encoding="utf-8")
        html_path.write_text(html, encoding="utf-8")
        written.append(md_path.name)
        written.append(html_path.name)

    print(f"Wrote {len(written)} files to {OUTPUT_DIR}")
    for name in written:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
