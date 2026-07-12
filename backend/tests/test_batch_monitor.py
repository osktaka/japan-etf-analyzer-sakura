"""Regression tests for scripts/batch_monitor.py.

過去バグ: PROJECT_ROOT を parent.parent.parent で計算していたため、コンテナ実行
(__file__=/app/scripts/batch_monitor.py) では PROJECT_ROOT が "/" に解決され、
リトライ対象スクリプトを常に見失っていた（本番ログに Script not found が残存）。
このテストは PROJECT_ROOT がアプリルート(scripts/ の親)を指し、BATCH_SCRIPTS の
各エントリが実在ファイルへ解決されることを保証する。
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# scripts ディレクトリを sys.path に追加
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import batch_monitor as m  # noqa: E402


def test_project_root_points_to_app_root():
    """PROJECT_ROOT は scripts/ の親（=アプリルート）を指す。"""
    assert m.PROJECT_ROOT == SCRIPTS_DIR.parent
    # scripts/ ディレクトリが直下に存在する
    assert (m.PROJECT_ROOT / "scripts").is_dir()


def test_batch_scripts_resolve_to_existing_files():
    """BATCH_SCRIPTS の各スクリプトが PROJECT_ROOT 配下で実在する。

    parent.parent.parent 退行が再発すると全エントリが exists()=False になり
    リトライが無言で停止するため、このアサートが退行を検知する。
    """
    assert m.BATCH_SCRIPTS, "BATCH_SCRIPTS が空"
    for batch_name, rel_path in m.BATCH_SCRIPTS.items():
        full = m.PROJECT_ROOT / rel_path
        assert full.exists(), f"{batch_name}: {full} が存在しない（パス解決の退行）"


def test_batch_scripts_paths_are_relative():
    """BATCH_SCRIPTS の値は PROJECT_ROOT 相対（先頭スラッシュなし）である。"""
    for batch_name, rel_path in m.BATCH_SCRIPTS.items():
        assert not rel_path.startswith("/"), f"{batch_name}: 絶対パスは不可"
        assert rel_path.startswith("scripts/"), f"{batch_name}: scripts/ 相対であること"


# ---- 最終失敗通知（1-2） -----------------------------------------------


def _fake_job(job_id=999, retry_count=3):
    return SimpleNamespace(
        id=job_id,
        batch_name="update_etf_data",
        retry_count=retry_count,
        error_message="boom",
    )


def test_final_failure_alert_disabled_by_default(monkeypatch, tmp_path):
    """BATCH_ALERT_ENABLED 未設定なら送信もマーカー作成もしない。"""
    monkeypatch.delenv("BATCH_ALERT_ENABLED", raising=False)
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)
    (tmp_path / "logs").mkdir()
    fake_client = MagicMock()
    monkeypatch.setattr(m, "EmailClient", MagicMock(return_value=fake_client))

    m.BatchMonitorScript()._notify_final_failure(_fake_job())

    fake_client.send.assert_not_called()
    assert not (tmp_path / "logs" / ".batch_alert_999").exists()


def test_final_failure_alert_sends_once_and_is_idempotent(monkeypatch, tmp_path):
    """有効時は1回送信しマーカーを作成、以降は再送しない（冪等）。"""
    monkeypatch.setenv("BATCH_ALERT_ENABLED", "1")
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)
    (tmp_path / "logs").mkdir()
    fake_client = MagicMock()
    fake_client.send.return_value = True
    monkeypatch.setattr(m, "EmailClient", MagicMock(return_value=fake_client))

    script = m.BatchMonitorScript()
    script._notify_final_failure(_fake_job())
    script._notify_final_failure(_fake_job())  # 2回目

    assert fake_client.send.call_count == 1  # 冪等
    assert (tmp_path / "logs" / ".batch_alert_999").exists()


def test_final_failure_alert_no_marker_when_send_fails(monkeypatch, tmp_path):
    """送信失敗(False)時はマーカーを作らず、次回に再送を許す。"""
    monkeypatch.setenv("BATCH_ALERT_ENABLED", "1")
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)
    (tmp_path / "logs").mkdir()
    fake_client = MagicMock()
    fake_client.send.return_value = False
    monkeypatch.setattr(m, "EmailClient", MagicMock(return_value=fake_client))

    m.BatchMonitorScript()._notify_final_failure(_fake_job())

    assert not (tmp_path / "logs" / ".batch_alert_999").exists()
