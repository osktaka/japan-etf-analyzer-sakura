"""AdvisorRunner がJSTベースで日付を扱うことを検証する.

JST 07:00 = UTC 22:00（前日）になるため、UTC基準のままだと
朝メールが「前日の日付」で送信される不具合の回帰防止.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# scripts ディレクトリをsys.pathに追加（_shared パッケージのため）
SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _shared.advisor_runner import JST, AdvisorRunner  # noqa: E402


def test_jst_constant_is_asia_tokyo():
    """JSTモジュール定数が Asia/Tokyo であること."""
    assert JST == ZoneInfo("Asia/Tokyo")


def test_run_uses_jst_today(tmp_path):
    """run() の today が JST 基準で計算されること.

    UTC 2026-04-29 22:00 = JST 2026-04-30 07:00 のとき、
    today が 2026-04-30 (JST日付) になることを検証する.
    """
    # UTC 22:00 (= JST 翌日 07:00)
    utc_now = datetime(2026, 4, 29, 22, 0, 0, tzinfo=ZoneInfo("UTC"))

    runner = AdvisorRunner(
        project_root=tmp_path,
        strategy_file=tmp_path / "dummy_strategy.md",
        reports_dir=tmp_path / "reports",
        user_id_str="test",
        dry_run=True,
    )

    captured_today: dict = {}

    def _capture_build_context(self, kind, strategy, deps, today):
        captured_today["today"] = today
        # ダミーのctxを返してrender失敗で抜ける
        return None

    # _import_late と StrategyLoader.load をモックし、
    # _build_context を差し替えて today をキャプチャ
    fake_strategy = MagicMock()
    fake_loader = MagicMock()
    fake_loader.load.return_value = fake_strategy
    deps = {"StrategyLoader": fake_loader}

    with patch("_shared.advisor_runner._import_late", return_value=deps), \
         patch("_shared.advisor_runner.datetime") as mock_dt, \
         patch.object(AdvisorRunner, "_build_context", _capture_build_context):
        # datetime.now(JST) のみJST基準時刻を返すよう設定
        mock_dt.now.side_effect = lambda tz=None: utc_now.astimezone(tz) if tz else utc_now
        # date クラスは元のものをそのまま使う
        rc = runner.run("morning")

    # _build_context が None を返したため失敗扱い (1)
    assert rc == 1
    # JST基準では翌日 (2026-04-30) になっていること
    assert captured_today["today"] == date(2026, 4, 30)


def test_write_markdown_alert_uses_jst_timestamp(tmp_path):
    """alertのファイル名のHHMMSSがJST基準であること."""
    runner = AdvisorRunner(
        project_root=tmp_path,
        strategy_file=tmp_path / "dummy.md",
        reports_dir=tmp_path / "reports",
        user_id_str="test",
        dry_run=True,
    )

    # UTC 2026-04-29 22:30:45 = JST 2026-04-30 07:30:45
    utc_now = datetime(2026, 4, 29, 22, 30, 45, tzinfo=ZoneInfo("UTC"))
    today_jst = date(2026, 4, 30)

    with patch("_shared.advisor_runner.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz=None: utc_now.astimezone(tz) if tz else utc_now
        path = runner._write_markdown("alert", today_jst, "dummy content")

    # ファイル名: {YYYYMMDD}_alert_{HHMMSS}.md, JST=07:30:45
    assert path.name == "20260430_alert_073045.md"
    assert path.exists()
