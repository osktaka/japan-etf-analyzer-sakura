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
