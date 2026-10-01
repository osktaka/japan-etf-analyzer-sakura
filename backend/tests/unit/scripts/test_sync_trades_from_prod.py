"""sync_trades_from_prod.py のガードと取得部の振る舞い.

本番シェルでの誤実行防止（コンテナ外は拒否）と、Bearer キーを平文で送らない
https 制限は、コンテナ内で手動確認しづらいため単体で固定する。
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import sync_trades_from_prod as sync  # noqa: E402


class TestGuard:
    def test_refuses_outside_container_before_touching_app(self, monkeypatch, capsys):
        monkeypatch.setattr(sync, "in_container", lambda: False)
        monkeypatch.setattr(sys, "argv", ["sync_trades_from_prod.py"])
        called = MagicMock()
        monkeypatch.setattr(sync, "fetch_remote", called)

        assert sync.main() == 2

        assert "outside the local Docker container" in capsys.readouterr().out
        called.assert_not_called()


class TestFetchRemote:
    def test_refuses_non_https_remote_host(self, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        get = MagicMock()
        monkeypatch.setattr(sync.requests, "get", get)
        with pytest.raises(RuntimeError, match="non-https"):
            sync.fetch_remote("http://example.com", "test")
        get.assert_not_called()

    @pytest.mark.parametrize(
        "url", ["http://localhost.evil.com", "http://127.0.0.1@evil.com"]
    )
    def test_refuses_lookalike_hosts(self, monkeypatch, url):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        with pytest.raises(RuntimeError, match="non-https"):
            sync.fetch_remote(url, "test")

    def test_empty_key_stops_before_request(self, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "")
        get = MagicMock()
        monkeypatch.setattr(sync.requests, "get", get)
        with pytest.raises(RuntimeError, match="NOTES_API_KEY is empty"):
            sync.fetch_remote("https://example.com", "test")
        get.assert_not_called()

    def test_non_json_body_becomes_runtime_error(self, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        resp = MagicMock(status_code=200)
        resp.json.side_effect = ValueError("not json")
        monkeypatch.setattr(sync.requests, "get", MagicMock(return_value=resp))
        with pytest.raises(RuntimeError, match="unexpected response body"):
            sync.fetch_remote("https://example.com", "test")

    def test_http_localhost_allowed(self, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"data": {"trades": [], "cash_flows": []}}
        monkeypatch.setattr(sync.requests, "get", MagicMock(return_value=resp))
        assert sync.fetch_remote("http://localhost:8902", "test")["trades"] == []


class TestAutoMode:
    """--auto（cron 用）: 差分なしは行を作らず、ローカルで登録した行は消さずに失敗を残す。"""

    @pytest.fixture
    def env(self, app, db_session, monkeypatch, tmp_path):
        from datetime import date

        from src.models import ETF, BatchLog, Category, Trade, User
        from src.services.user_data_sync_service import export_user_data

        cat = Category(name="c")
        db_session.add(cat)
        db_session.commit()
        db_session.add(ETF(code="1615", name="1615", category_id=cat.id))
        user = User(user_id="test", password_hash="x", username="t")
        db_session.add(user)
        db_session.commit()
        monkeypatch.setattr(sync, "in_container", lambda: True)
        monkeypatch.setattr("src.app.create_app", lambda *a, **k: app)
        monkeypatch.setattr(sys, "argv", ["sync_trades_from_prod.py", "--auto"])
        # :memory: DB には実体が無く、本物の backup_db / snapshot_path は cwd にゴミを作る
        monkeypatch.setattr(sync, "backup_db", lambda *a, **k: "backup-stub")
        monkeypatch.setattr(
            sync, "snapshot_path", lambda *a, **k: tmp_path / "snap.json"
        )
        alerts = []
        monkeypatch.setattr(sync, "send_failure_alert", alerts.append)

        class Env:
            pass

        e = Env()
        e.alerts = alerts
        e.user_pk = user.id
        e.Trade = Trade

        def add_local(qty):
            db_session.add(
                Trade(
                    user_id=user.id,
                    etf_code="1615",
                    trade_type="buy",
                    quantity=qty,
                    price=100.0,
                    trade_date=date(2026, 9, 1),
                )
            )
            db_session.commit()

        def logs():
            return [
                log.status
                for log in BatchLog.query.filter_by(batch_name=sync.BATCH_NAME)
                .order_by(BatchLog.id)
                .all()
            ]

        def remote(edit=lambda rows: rows):
            """ローカルの現在値を本番の姿とし、edit で本番側の訂正・追加・削除を表す。"""
            data = export_user_data(user.id)
            rows = edit([dict(r) for r in data["trades"]])
            monkeypatch.setattr(
                sync,
                "fetch_remote",
                lambda *a, **k: {"trades": rows, "cash_flows": []},
            )

        def qtys():
            return sorted(t.quantity for t in Trade.query.all())

        e.add_local, e.logs, e.remote, e.qtys = add_local, logs, remote, qtys
        return e

    def test_in_sync_writes_no_batch_log(self, env):
        env.add_local(10)
        env.remote()

        assert sync.main() == 0
        assert env.logs() == []

    def test_adds_remote_rows_and_logs_success(self, env):
        env.add_local(10)
        env.remote(lambda rows: rows + [{**rows[0], "quantity": 20}])

        assert sync.main() == 0
        assert env.qtys() == [10, 20]
        assert env.logs() == ["success"]

    def test_remote_edit_is_applied_after_first_sync(self, env):
        env.add_local(10)
        env.remote()
        assert sync.main() == 0  # 差分なし。ここで前回同期のスナップショットができる
        env.remote(lambda rows: [{**rows[0], "quantity": 11}])  # 本番で訂正

        assert sync.main() == 0
        assert env.qtys() == [11]
        assert env.logs() == ["success"]

    def test_remote_delete_is_applied_after_first_sync(self, env):
        env.add_local(10)
        env.add_local(20)
        env.remote()
        assert sync.main() == 0
        env.remote(lambda rows: rows[:1])  # 本番で1件削除

        assert sync.main() == 0
        assert len(env.qtys()) == 1

    def test_refuses_locally_registered_row(self, env):
        env.add_local(10)
        env.remote()
        assert sync.main() == 0  # スナップショット作成
        env.add_local(99)  # 同期後にローカルで登録（本番に無い）
        env.remote(lambda rows: rows[:1])

        assert sync.main() == 1
        assert env.qtys() == [10, 99]
        assert env.logs() == ["failed"]

    def test_refuses_without_snapshot(self, env):
        env.add_local(10)
        env.add_local(99)
        env.remote(lambda rows: rows[:1])  # スナップショット無し → 判別できず安全側

        assert sync.main() == 1
        assert env.qtys() == [10, 99]

    def test_failure_streak_logs_and_alerts_once_then_recovers(self, env, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("HTTP 503")

        monkeypatch.setattr(sync, "fetch_remote", boom)
        assert sync.main() == 1
        assert sync.main() == 1
        assert env.logs() == ["failed"]
        assert len(env.alerts) == 1

        env.add_local(10)
        env.remote()
        assert sync.main() == 0
        assert env.logs() == ["failed", "success"]  # 復旧の記録

        monkeypatch.setattr(sync, "fetch_remote", boom)
        assert sync.main() == 1
        assert env.logs() == ["failed", "success", "failed"]
        assert len(env.alerts) == 2

    def test_manual_run_writes_no_batch_log(self, env, monkeypatch):
        env.add_local(10)
        env.remote(lambda rows: rows + [{**rows[0], "quantity": 20}])
        monkeypatch.setattr(sys, "argv", ["sync_trades_from_prod.py"])  # dry-run

        assert sync.main() == 0
        assert env.qtys() == [10]
        assert env.logs() == []

    def test_restore_does_not_poison_snapshot(self, env, monkeypatch, tmp_path):
        from src.services.user_data_sync_service import export_user_data

        env.add_local(10)
        env.remote()
        assert sync.main() == 0  # スナップショット作成（行 10 のみ）
        env.add_local(99)
        backup_view = export_user_data(env.user_pk)  # 99 を含むバックアップに見立てる
        env.Trade.query.filter_by(quantity=99).delete()
        env.Trade.query.session.commit()
        monkeypatch.setattr(
            "src.services.user_data_sync_service.read_user_data_from_sqlite",
            lambda *a, **k: backup_view,
        )
        backup = tmp_path / "b.db"
        backup.write_bytes(b"")
        monkeypatch.setattr(
            sys,
            "argv",
            ["sync_trades_from_prod.py", "--restore-from", str(backup), "--execute"],
        )
        assert sync.main() == 0
        assert env.qtys() == [10, 99]  # 復元でローカルに戻った
        env.remote(lambda rows: rows[:1])  # 本番には 99 が無い
        monkeypatch.setattr(sys, "argv", ["sync_trades_from_prod.py", "--auto"])

        assert sync.main() == 1  # 復元行は消さずに拒否
        assert env.qtys() == [10, 99]

    def test_failure_kind_change_logs_and_alerts_again(self, env, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("HTTP 503")

        monkeypatch.setattr(sync, "fetch_remote", boom)
        assert sync.main() == 1  # source failed
        env.add_local(10)
        env.add_local(99)
        env.remote(lambda rows: rows[:1])
        assert sync.main() == 1  # 種類が変わった（locally registered rows）

        assert env.logs() == ["failed", "failed"]
        assert len(env.alerts) == 2
