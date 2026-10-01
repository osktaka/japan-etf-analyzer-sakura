"""Integration tests for the prod -> local sync export endpoint."""
from datetime import date

import pytest

from src.models import ETF, CashFlow, Category, Trade, User


@pytest.fixture
def data(db_session):
    cat = Category(name="c")
    db_session.add(cat)
    db_session.commit()
    db_session.add(ETF(code="1615", name="n", category_id=cat.id))
    user = User(user_id="test", password_hash="x", username="t")
    db_session.add(user)
    db_session.commit()
    db_session.add(
        Trade(
            user_id=user.id,
            etf_code="1615",
            trade_type="buy",
            quantity=3,
            price=10,
            trade_date=date(2026, 9, 1),
        )
    )
    db_session.add(
        CashFlow(
            user_id=user.id, flow_type="deposit", amount=100, flow_date=date(2026, 9, 1)
        )
    )
    db_session.commit()


class TestSyncUserData:
    URL = "/api/v1/sync/user-data"

    def test_requires_api_key(self, client, data, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        assert client.get(self.URL + "?user_id=test").status_code == 403
        r = client.get(
            self.URL + "?user_id=test", headers={"Authorization": "Bearer wrong"}
        )
        assert r.status_code == 403

    def test_returns_trades_and_cash_flows(self, client, data, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        r = client.get(
            self.URL + "?user_id=test", headers={"Authorization": "Bearer k"}
        )
        body = r.get_json()["data"]
        assert r.status_code == 200
        assert body["trades"][0]["etf_code"] == "1615"
        assert body["cash_flows"][0]["amount"] == 100.0
        assert body["summary"]["trade_count"] == 1

    def test_user_outside_allowlist_403(self, client, data, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        r = client.get(
            self.URL + "?user_id=someone", headers={"Authorization": "Bearer k"}
        )
        assert r.status_code == 403

    def test_allowlist_configurable(self, client, data, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        monkeypatch.setenv("SYNC_EXPORT_USER_IDS", "test, other")
        r = client.get(
            self.URL + "?user_id=other", headers={"Authorization": "Bearer k"}
        )
        assert r.status_code == 404  # 許可されたが存在しない

    def test_unknown_user_404(self, client, data, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        monkeypatch.setenv("SYNC_EXPORT_USER_IDS", "test,nobody")
        r = client.get(
            self.URL + "?user_id=nobody", headers={"Authorization": "Bearer k"}
        )
        assert r.status_code == 404

    def test_user_id_required(self, client, data, monkeypatch):
        monkeypatch.setenv("NOTES_API_KEY", "k")
        r = client.get(self.URL, headers={"Authorization": "Bearer k"})
        assert r.status_code == 400
