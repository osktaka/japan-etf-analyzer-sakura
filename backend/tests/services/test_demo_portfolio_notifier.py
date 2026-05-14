"""Unit tests for src/services/demo_portfolio_notifier.py.

実HTTP / 実SMTP / DB は使わない。すべてモック。
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.services import demo_portfolio_notifier as notifier


# ---- ヘルパー ------------------------------------------------------------

def _trade_result(
    etf_code: str = "1306",
    trade_type: str = "buy",
    quantity: int = 10,
    price: float = 2500.0,
    status: str = "success",
    http_status: int | None = 201,
    error_message: str | None = None,
    memo: str = "[auto] x",
):
    return {
        "etf_code": etf_code,
        "trade_type": trade_type,
        "quantity": quantity,
        "price": price,
        "memo": memo,
        "status": status,
        "http_status": http_status,
        "error_message": error_message,
    }


def _portfolio_snapshot(
    total_asset: float | None = 1_015_200,
    pct: float | None = 1.2,
    holdings: list | None = None,
):
    """API レスを模した snapshot."""
    portfolio = (
        None
        if total_asset is None
        else {
            "total_asset": total_asset,
            "total_value": total_asset,
            "cash_balance": 100_000,
            "holdings_count": 2,
            "daily_change_total_asset": (total_asset * pct / 100.0) if pct else 0,
            "daily_change_total_asset_percent": pct,
        }
    )
    return {
        "portfolio": portfolio,
        "holdings": holdings if holdings is not None else [],
        "valuation_history": [],
        "errors": [] if portfolio else ["portfolio", "holdings", "valuation_history"],
    }


# ---- should_send --------------------------------------------------------

class TestShouldSend:
    def test_should_send_disabled(self):
        assert notifier.should_send("always", enabled=False, dry_run=False, succeeded=1, failed=0) is False

    def test_should_send_never(self):
        assert notifier.should_send("never", enabled=True, dry_run=False, succeeded=1, failed=0) is False

    def test_should_send_always_with_dry_run(self):
        assert notifier.should_send("always", enabled=True, dry_run=True, succeeded=0, failed=0) is True

    def test_should_send_on_trade_with_executions(self):
        assert notifier.should_send("on_trade", enabled=True, dry_run=False, succeeded=1, failed=0) is True

    def test_should_send_on_trade_dry_run_false(self):
        assert notifier.should_send("on_trade", enabled=True, dry_run=True, succeeded=1, failed=0) is False

    def test_should_send_on_trade_no_trades_false(self):
        assert notifier.should_send("on_trade", enabled=True, dry_run=False, succeeded=0, failed=0) is False


# ---- build_subject ------------------------------------------------------

class TestBuildSubject:
    TODAY = date(2026, 5, 14)

    def test_build_subject_success_only(self):
        results = [_trade_result(status="success"), _trade_result(status="success")]
        snap = _portfolio_snapshot(total_asset=1_015_200, pct=1.2)
        subj = notifier.build_subject(results, snap, self.TODAY, dry_run=False)
        assert "[5/14 demo]" in subj
        assert "取引2件" in subj
        assert "¥1,015,200" in subj
        assert "+1.2%" in subj

    def test_build_subject_partial_failure(self):
        results = [_trade_result(status="success"), _trade_result(status="failed")]
        snap = _portfolio_snapshot()
        subj = notifier.build_subject(results, snap, self.TODAY, dry_run=False)
        assert "⚠️" in subj  # ⚠️
        assert "1/2件成功" in subj

    def test_build_subject_all_failed(self):
        results = [_trade_result(status="failed"), _trade_result(status="failed")]
        snap = _portfolio_snapshot()
        subj = notifier.build_subject(results, snap, self.TODAY, dry_run=False)
        assert "❌" in subj  # ❌
        assert "全失敗" in subj

    def test_build_subject_dry_run(self):
        results = [_trade_result(status="dry_run")]
        snap = _portfolio_snapshot()
        subj = notifier.build_subject(results, snap, self.TODAY, dry_run=True)
        assert "dry-run" in subj

    def test_build_subject_within_40_chars(self):
        snap = _portfolio_snapshot(total_asset=9_999_999, pct=12.3)
        for results, dry_run in [
            ([_trade_result(status="success")], False),
            ([_trade_result(status="success"), _trade_result(status="failed")], False),
            ([_trade_result(status="failed"), _trade_result(status="failed")], False),
            ([_trade_result(status="dry_run")], True),
        ]:
            subj = notifier.build_subject(results, snap, self.TODAY, dry_run=dry_run)
            assert len(subj) <= notifier.SUBJECT_MAX_LEN, f"len={len(subj)} subj={subj!r}"


# ---- render_email -------------------------------------------------------

class TestRenderEmail:
    TODAY = date(2026, 5, 14)

    def test_render_email_returns_md_and_html(self):
        results = [_trade_result(status="success")]
        snap = _portfolio_snapshot(
            total_asset=1_015_200,
            pct=1.2,
            holdings=[
                {
                    "etf_code": "1306",
                    "current_value": 500_000,
                    "current_price": 2500,
                    "quantity": 200,
                    "unrealized_pnl": 1000,
                    "unrealized_pnl_percent": 0.5,
                    "etf_info": {"name": "TOPIX連動"},
                }
            ],
        )
        md, html = notifier.render_email(
            results, snap, self.TODAY, dry_run=False, batch_log_id=99
        )
        assert isinstance(md, str) and isinstance(html, str)
        assert len(md) > 0 and len(html) > 0
        assert "1306" in md
        assert "1306" in html

    def test_render_email_graceful_degrade(self):
        """snapshot.portfolio=None でもレンダリング成功."""
        results = [_trade_result(status="success")]
        snap = _portfolio_snapshot(total_asset=None)
        md, html = notifier.render_email(
            results, snap, self.TODAY, dry_run=False, batch_log_id=None
        )
        assert "データ取得失敗" in md
        # html はエスケープ次第だが、portfolio が無い分岐のテキストは含まれるはず
        assert "データ取得失敗" in html


# ---- fetch_portfolio_snapshot ------------------------------------------

class TestFetchPortfolioSnapshot:
    def test_fetch_portfolio_snapshot_collects_errors(self):
        """3 API 全失敗で errors に3件入る."""
        import requests as _req
        with patch.object(
            _req,
            "get",
            side_effect=_req.RequestException("network down"),
        ):
            snap = notifier.fetch_portfolio_snapshot("http://localhost:8902")
        assert snap["portfolio"] is None
        assert snap["holdings"] is None
        assert snap["valuation_history"] is None
        assert set(snap["errors"]) == {"portfolio", "holdings", "valuation_history"}


# ---- notify (エントリポイント) ----------------------------------------

class TestNotify:
    TODAY = date(2026, 5, 14)

    def test_notify_smtp_failure_returns_false(self, monkeypatch):
        """EmailClient.send が False のとき notify も False を返し例外を伝播しない."""
        monkeypatch.setenv("DEMO_PORTFOLIO_REPORT_ENABLED", "1")
        monkeypatch.setenv("DEMO_PORTFOLIO_REPORT_TRIGGER", "always")
        mock_client = MagicMock()
        mock_client.send.return_value = False
        with patch.object(
            notifier, "fetch_portfolio_snapshot", return_value=_portfolio_snapshot()
        ), patch.object(notifier, "EmailClient", return_value=mock_client):
            ok = notifier.notify(
                trade_results=[_trade_result(status="success")],
                today_jst=self.TODAY,
                dry_run=False,
                batch_log_id=1,
                base_url="http://localhost:8902",
            )
        assert ok is False
        mock_client.send.assert_called_once()

    def test_notify_disabled_returns_false(self, monkeypatch):
        """DEMO_PORTFOLIO_REPORT_ENABLED 未設定なら False で即終了."""
        monkeypatch.delenv("DEMO_PORTFOLIO_REPORT_ENABLED", raising=False)
        ok = notifier.notify(
            trade_results=[_trade_result(status="success")],
            today_jst=self.TODAY,
            dry_run=False,
            batch_log_id=1,
        )
        assert ok is False

    def test_notify_success_returns_true(self, monkeypatch):
        """正常系: enabled + trigger 一致 + send True で True."""
        monkeypatch.setenv("DEMO_PORTFOLIO_REPORT_ENABLED", "1")
        monkeypatch.setenv("DEMO_PORTFOLIO_REPORT_TRIGGER", "on_trade")
        mock_client = MagicMock()
        mock_client.send.return_value = True
        with patch.object(
            notifier, "fetch_portfolio_snapshot", return_value=_portfolio_snapshot()
        ), patch.object(notifier, "EmailClient", return_value=mock_client):
            ok = notifier.notify(
                trade_results=[_trade_result(status="success")],
                today_jst=self.TODAY,
                dry_run=False,
                batch_log_id=1,
            )
        assert ok is True

    def test_notify_render_failure_returns_false(self, monkeypatch):
        """render_email が例外を投げても捕捉して False."""
        monkeypatch.setenv("DEMO_PORTFOLIO_REPORT_ENABLED", "1")
        monkeypatch.setenv("DEMO_PORTFOLIO_REPORT_TRIGGER", "always")
        with patch.object(
            notifier, "fetch_portfolio_snapshot", return_value=_portfolio_snapshot()
        ), patch.object(
            notifier, "render_email", side_effect=RuntimeError("template broken")
        ):
            ok = notifier.notify(
                trade_results=[_trade_result(status="success")],
                today_jst=self.TODAY,
                dry_run=False,
                batch_log_id=1,
            )
        assert ok is False
