"""Unit tests for scripts/execute_demo_trades.py.

DBや実HTTP通信は行わない。すべてモック。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# scripts ディレクトリを sys.path に追加
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import execute_demo_trades as m  # noqa: E402


# ---- ヘルパー -----------------------------------------------------------

def _make_plan(tmp_path: Path, user: str, trades: list) -> Path:
    """reports/{user}/trades_execution_plan.json を作成して返す."""
    user_dir = tmp_path / "reports" / user
    user_dir.mkdir(parents=True, exist_ok=True)
    plan = user_dir / "trades_execution_plan.json"
    plan.write_text(json.dumps({"trades": trades}, ensure_ascii=False), encoding="utf-8")
    return plan


def _trade(etf="1306", trade_type="buy", quantity=10, price=2500.0, plan_id="P1", memo=""):
    return {
        "plan_id": plan_id,
        "etf_code": etf,
        "trade_type": trade_type,
        "quantity": quantity,
        "price": price,
        "memo": memo,
    }


def _existing(etf="1306", trade_type="buy", memo="[auto][plan_id=P1] x"):
    return SimpleNamespace(etf_code=etf, trade_type=trade_type, memo=memo)


@pytest.fixture
def patched_main(tmp_path, monkeypatch):
    """main() を「DBなし」で動かすための共通モック.

    Returns
    -------
    dict
        argv 設定や fakes（trade_repo / user_repo / batch_repo / post）を含む.
    """
    monkeypatch.setattr(m, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("DEMO_TRADE_POST_ENABLED", "1")

    fake_user = SimpleNamespace(id=1, user_id="demo")
    user_repo = MagicMock()
    user_repo.get_by_user_id.return_value = fake_user

    trade_repo = MagicMock()
    trade_repo.get_by_date_range.return_value = []

    batch_log = SimpleNamespace(id=99)
    batch_repo = MagicMock()
    batch_repo.create.return_value = batch_log

    fake_app = MagicMock()
    fake_app.app_context.return_value.__enter__.return_value = None
    fake_app.app_context.return_value.__exit__.return_value = False

    post_mock = MagicMock(return_value=(True, "HTTP 201"))

    # 既定は portfolio state 取得失敗扱い（{}）= pre-check スキップで従来挙動を維持。
    # 個別テストで返り値を差し替えて検証ゲートをテストする。
    state_mock = MagicMock(return_value={})

    monkeypatch.setattr(m, "create_app", lambda: fake_app)
    monkeypatch.setattr(m, "UserRepository", lambda: user_repo)
    monkeypatch.setattr(m, "TradeRepository", lambda: trade_repo)
    monkeypatch.setattr(m, "BatchLogRepository", lambda: batch_repo)
    monkeypatch.setattr(m, "post_trade", post_mock)
    monkeypatch.setattr(m, "fetch_portfolio_state", state_mock)
    monkeypatch.setattr(m, "fetch_reference_price", lambda *a, **k: None)

    return {
        "user_repo": user_repo,
        "trade_repo": trade_repo,
        "batch_repo": batch_repo,
        "post": post_mock,
        "state": state_mock,
    }


def _run_main(argv: list[str]) -> int:
    with patch.object(sys, "argv", argv):
        return m.main()


# ---- ヘルパー関数のテスト ----------------------------------------------

class TestHelpers:
    def test_build_payload_includes_auto_marker(self):
        payload = m.build_payload(_trade(plan_id="P9", memo="買い増し"), "2026-05-14")
        assert payload["etf_code"] == "1306"
        assert payload["trade_type"] == "buy"
        assert payload["trade_date"] == "2026-05-14"
        assert "[auto]" in payload["memo"]
        assert "P9" in payload["memo"]

    def test_is_duplicate_returns_false_for_different_etf(self):
        existing = [_existing(etf="1306", memo="[auto][plan_id=P1] x")]
        # 別 ETF
        assert m.is_duplicate(_trade(etf="2516", plan_id="P1"), existing) is False

    def test_exit_code_all_success(self):
        assert m._exit_code(3, 0, 0) == 0

    def test_exit_code_partial(self):
        assert m._exit_code(2, 1, 0) == 2

    def test_exit_code_all_failed(self):
        assert m._exit_code(0, 2, 0) == 1


# ---- 検証ゲートのテスト -------------------------------------------------

class TestValidateTrade:
    def test_buy_within_cash_ok(self):
        state = {"cash_balance": 100000, "holdings": {}}
        assert m.validate_trade(_trade(quantity=10, price=2500), state, None) is None

    def test_buy_exceeds_cash_rejected(self):
        state = {"cash_balance": 10000, "holdings": {}}
        reason = m.validate_trade(_trade(quantity=10, price=2500), state, None)
        assert reason is not None and "現金不足" in reason

    def test_sell_within_holdings_ok(self):
        state = {"cash_balance": 0, "holdings": {"1306": 20}}
        t = _trade(etf="1306", trade_type="sell", quantity=10, price=2500)
        assert m.validate_trade(t, state, None) is None

    def test_sell_exceeds_holdings_rejected(self):
        state = {"cash_balance": 0, "holdings": {"1306": 5}}
        t = _trade(etf="1306", trade_type="sell", quantity=10, price=2500)
        reason = m.validate_trade(t, state, None)
        assert reason is not None and "保有超過" in reason

    def test_price_deviation_within_5pct_ok(self):
        state = {"cash_balance": 10**9, "holdings": {}}
        # 終値 2500 に対し +4%
        t = _trade(quantity=1, price=2600)
        assert m.validate_trade(t, state, reference_price=2500.0) is None

    def test_price_deviation_over_5pct_rejected(self):
        state = {"cash_balance": 10**9, "holdings": {}}
        t = _trade(quantity=1, price=2700)  # +8%
        reason = m.validate_trade(t, state, reference_price=2500.0)
        assert reason is not None and "価格乖離" in reason

    def test_split_basis_mismatch_caught_by_deviation(self):
        """分割基準ズレ（例: 2:1 で価格が約2倍）は乖離チェックで弾かれる."""
        state = {"cash_balance": 10**9, "holdings": {}}
        t = _trade(quantity=1, price=5000)  # 終値2500の2倍
        reason = m.validate_trade(t, state, reference_price=2500.0)
        assert reason is not None and "価格乖離" in reason


# ---- main() の振る舞いテスト -------------------------------------------

class TestMain:
    def test_empty_trades_exit_0(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [])
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 0
        patched_main["post"].assert_not_called()

    def test_db_duplicate_skipped(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [_trade(plan_id="P1")])
        patched_main["trade_repo"].get_by_date_range.return_value = [
            _existing(etf="1306", trade_type="buy", memo="[auto][plan_id=P1] prev")
        ]
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 0
        patched_main["post"].assert_not_called()

    def test_dry_run_does_not_post(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [_trade(plan_id="P1")])
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--dry-run"])
        assert rc == 0
        patched_main["post"].assert_not_called()

    def test_prod_requires_confirm_production(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [_trade()])
        rc = _run_main([
            "execute_demo_trades.py", "--user", "demo", "--env", "prod", "--execute"
        ])
        assert rc == 1
        patched_main["post"].assert_not_called()

    def test_marker_early_exit(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [_trade()])
        # 当日マーカーを先に作っておく
        from datetime import datetime
        today = datetime.now(m.JST).date()
        marker = tmp_path / "reports" / "demo" / f".trades_posted_{today.strftime('%Y%m%d')}"
        marker.write_text("x", encoding="utf-8")
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 0
        patched_main["post"].assert_not_called()

    def test_plan_file_missing(self, patched_main, tmp_path):
        # プランファイルを作らない
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 0
        patched_main["post"].assert_not_called()

    def test_partial_failure_exit_2(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [
            _trade(etf="1306", plan_id="P1"),
            _trade(etf="2516", plan_id="P2"),
        ])
        patched_main["post"].side_effect = [
            (True, "HTTP 201"),
            (False, "HTTP 500: boom"),
        ]
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 2
        assert patched_main["post"].call_count == 2

    def test_gate_rejects_overdraw_buy_no_post(self, patched_main, tmp_path):
        """現金不足の買いは POST されず、全違反なので exit code 1."""
        _make_plan(tmp_path, "demo", [_trade(quantity=100, price=2500, plan_id="P1")])
        patched_main["state"].return_value = {"cash_balance": 1000, "holdings": {}}
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 1
        patched_main["post"].assert_not_called()

    def test_gate_partial_rejection_exit_2(self, patched_main, tmp_path):
        """1件違反 + 1件成功 → exit code 2、成功分のみ POST."""
        _make_plan(tmp_path, "demo", [
            _trade(etf="1306", quantity=100, price=2500, plan_id="P1"),
            _trade(etf="2516", quantity=1, price=2500, plan_id="P2"),
        ])
        patched_main["state"].return_value = {"cash_balance": 5000, "holdings": {}}
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 2
        assert patched_main["post"].call_count == 1

    def test_plan_id_null_uses_memo_prefix(self, patched_main, tmp_path):
        _make_plan(tmp_path, "demo", [_trade(plan_id=None, etf="1306", trade_type="buy")])
        patched_main["trade_repo"].get_by_date_range.return_value = [
            _existing(etf="1306", trade_type="buy", memo="[auto] manual earlier")
        ]
        rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])
        assert rc == 0
        patched_main["post"].assert_not_called()


# ---- 通知統合のテスト --------------------------------------------------

class TestNotifierIntegration:
    """demo_portfolio_notifier との統合（main 末尾の notify 呼び出し）."""

    def test_notify_called_after_post(self, patched_main, tmp_path):
        """main() の末尾で notifier.notify が1回呼ばれる."""
        _make_plan(tmp_path, "demo", [_trade(plan_id="P1")])
        from src.services import demo_portfolio_notifier as notifier_mod
        with patch.object(notifier_mod, "notify", return_value=True) as notify_mock:
            rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])

        assert rc == 0
        notify_mock.assert_called_once()
        call_kwargs = notify_mock.call_args.kwargs
        assert isinstance(call_kwargs["trade_results"], list)
        assert call_kwargs["dry_run"] is False
        assert call_kwargs["batch_log_id"] == 99

    def test_notify_disabled_does_not_call_email_client(
        self, patched_main, tmp_path, monkeypatch
    ):
        """DEMO_PORTFOLIO_REPORT_ENABLED 未設定時、内部で EmailClient.send が呼ばれない."""
        _make_plan(tmp_path, "demo", [_trade(plan_id="P1")])
        monkeypatch.delenv("DEMO_PORTFOLIO_REPORT_ENABLED", raising=False)

        from src.services import demo_portfolio_notifier as notifier_mod
        mock_client = MagicMock()
        with patch.object(
            notifier_mod, "EmailClient", return_value=mock_client
        ), patch.object(
            notifier_mod, "fetch_portfolio_snapshot", return_value={}
        ) as fetch_mock:
            rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])

        assert rc == 0
        mock_client.send.assert_not_called()
        # disabled の場合、fetch も呼ばれない（should_send で早期 False）
        fetch_mock.assert_not_called()

    def test_notify_failure_does_not_affect_exit_code(
        self, patched_main, tmp_path
    ):
        """notify が例外を投げても main() の exit code は変わらない."""
        _make_plan(tmp_path, "demo", [_trade(plan_id="P1")])
        from src.services import demo_portfolio_notifier as notifier_mod
        with patch.object(
            notifier_mod, "notify", side_effect=RuntimeError("notify crashed")
        ):
            rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--execute"])

        # 取引は全成功なので exit code = 0
        assert rc == 0
        patched_main["post"].assert_called_once()

    def test_results_includes_dry_run_status(self, patched_main, tmp_path):
        """dry-run モードで notify に渡される results が status='dry_run' を含む."""
        _make_plan(tmp_path, "demo", [_trade(plan_id="P1"), _trade(plan_id="P2", etf="2516")])
        from src.services import demo_portfolio_notifier as notifier_mod
        with patch.object(
            notifier_mod, "notify", return_value=False
        ) as notify_mock:
            rc = _run_main(["execute_demo_trades.py", "--user", "demo", "--dry-run"])

        assert rc == 0
        notify_mock.assert_called_once()
        results = notify_mock.call_args.kwargs["trade_results"]
        assert len(results) == 2
        assert all(r["status"] == "dry_run" for r in results)
        # POST は呼ばれていない
        patched_main["post"].assert_not_called()
