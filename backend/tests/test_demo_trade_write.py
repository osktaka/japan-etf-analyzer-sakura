"""Tests for demo write endpoints (POST trades, POST cash-flows)."""
import os

import pytest

import src.routes.demo_routes as demo_routes_module
from src.models import User
from src.models.etf import ETF

TEST_API_KEY = "test-demo-api-key"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture(autouse=True)
def reset_demo_user_cache():
    """Reset the module-level demo user PK cache before each test."""
    demo_routes_module._demo_user_pk = None
    yield
    demo_routes_module._demo_user_pk = None


@pytest.fixture(autouse=True)
def demo_api_key_env():
    """demo POST は api_key_required（NOTES_API_KEY共用）で保護されているため設定する."""
    os.environ["NOTES_API_KEY"] = TEST_API_KEY
    yield
    os.environ.pop("NOTES_API_KEY", None)


@pytest.fixture
def demo_user(db_session):
    """Create a demo user in the test database."""
    user = User(user_id="demo", username="Demo User")
    user.set_password("demopass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_etf(db_session):
    """Create a sample ETF for testing."""
    etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
    db_session.add(etf)
    db_session.commit()
    return etf


class TestCreateDemoTradeAuth:
    """demo POST endpoints require the api_key_required Authorization header."""

    def test_trades_requires_api_key(self, client, db_session, demo_user, sample_etf):
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
        )
        assert resp.status_code == 403
        assert resp.get_json()["success"] is False

    def test_cash_flows_requires_api_key(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/cash-flows",
            json={"flow_type": "deposit", "amount": 100000, "flow_date": "2025-04-01"},
        )
        assert resp.status_code == 403
        assert resp.get_json()["success"] is False

    def test_trades_rejects_wrong_api_key(
        self, client, db_session, demo_user, sample_etf
    ):
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 403


class TestCreateDemoTradeNoUser:
    """POST /api/v1/demo/trades when demo user does not exist."""

    def test_returns_404(self, client, db_session):
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["success"] is False


class TestCreateDemoTrade:
    """POST /api/v1/demo/trades with demo user present."""

    def test_buy_success(self, client, db_session, demo_user, sample_etf):
        client.post(
            "/api/v1/demo/cash-flows",
            json={"flow_type": "deposit", "amount": 100000, "flow_date": "2025-04-01"},
            headers=AUTH_HEADERS,
        )
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
                "memo": "[auto] テスト購入",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["etf_code"] == "1306"
        assert body["data"]["trade_type"] == "buy"
        assert body["data"]["quantity"] == 10
        assert body["message"] == "デモ取引を登録しました"

    def test_sell_success(self, client, db_session, demo_user, sample_etf):
        # 売却は保有を前提とするため、入金→買いで在庫を作ってから売る
        client.post(
            "/api/v1/demo/cash-flows",
            json={"flow_type": "deposit", "amount": 100000, "flow_date": "2025-04-01"},
            headers=AUTH_HEADERS,
        )
        client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "sell",
                "quantity": 5,
                "price": 2500.0,
                "trade_date": "2025-05-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["data"]["trade_type"] == "sell"

    def test_missing_required_field(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/trades",
            json={"etf_code": "1306", "trade_type": "buy"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["success"] is False

    def test_empty_body(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/trades",
            content_type="application/json",
            data="",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400

    def test_invalid_trade_type(self, client, db_session, demo_user, sample_etf):
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "invalid",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400

    def test_nonexistent_etf(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "9999",
                "trade_type": "buy",
                "quantity": 10,
                "price": 100.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400

    def test_trade_appears_in_get(self, client, db_session, demo_user, sample_etf):
        """Created trade should appear in GET /api/v1/demo/trades."""
        client.post(
            "/api/v1/demo/cash-flows",
            json={"flow_type": "deposit", "amount": 100000, "flow_date": "2025-04-01"},
            headers=AUTH_HEADERS,
        )
        client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        resp = client.get("/api/v1/demo/trades")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 1
        assert body["data"][0]["etf_code"] == "1306"


class TestCreateDemoTradeBalanceGuard:
    """残高・保有数量を超える取引はサーバ側で 400 拒否される."""

    def _deposit(self, client, amount):
        return client.post(
            "/api/v1/demo/cash-flows",
            json={"flow_type": "deposit", "amount": amount, "flow_date": "2025-04-01"},
            headers=AUTH_HEADERS,
        )

    def test_buy_exceeds_cash_rejected(self, client, db_session, demo_user, sample_etf):
        # 現金 0 のまま買い → 拒否
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400
        assert "現金残高が不足" in resp.get_json()["error"]["message"]

    def test_buy_within_cash_ok(self, client, db_session, demo_user, sample_etf):
        self._deposit(client, 100000)
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 201

    def test_sell_exceeds_holdings_rejected(
        self, client, db_session, demo_user, sample_etf
    ):
        self._deposit(client, 100000)
        client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 5,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "sell",
                "quantity": 10,
                "price": 2500.0,
                "trade_date": "2025-05-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400
        assert "保有数量を超える" in resp.get_json()["error"]["message"]

    def test_sell_within_holdings_ok(self, client, db_session, demo_user, sample_etf):
        self._deposit(client, 100000)
        client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2450.0,
                "trade_date": "2025-04-10",
            },
            headers=AUTH_HEADERS,
        )
        resp = client.post(
            "/api/v1/demo/trades",
            json={
                "etf_code": "1306",
                "trade_type": "sell",
                "quantity": 5,
                "price": 2500.0,
                "trade_date": "2025-05-10",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 201


class TestCreateDemoCashFlowNoUser:
    """POST /api/v1/demo/cash-flows when demo user does not exist."""

    def test_returns_404(self, client, db_session):
        resp = client.post(
            "/api/v1/demo/cash-flows",
            json={
                "flow_type": "deposit",
                "amount": 100000,
                "flow_date": "2025-04-01",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404


class TestCreateDemoCashFlow:
    """POST /api/v1/demo/cash-flows with demo user present."""

    def test_deposit_success(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/cash-flows",
            json={
                "flow_type": "deposit",
                "amount": 100000,
                "flow_date": "2025-04-01",
                "memo": "[auto] 追加入金",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"]["flow_type"] == "deposit"
        assert body["message"] == "デモ入出金を登録しました"

    def test_missing_required_field(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/cash-flows",
            json={"flow_type": "deposit"},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400

    def test_invalid_flow_type(self, client, db_session, demo_user):
        resp = client.post(
            "/api/v1/demo/cash-flows",
            json={
                "flow_type": "invalid",
                "amount": 100000,
                "flow_date": "2025-04-01",
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 400
