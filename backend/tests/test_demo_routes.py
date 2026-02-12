"""Integration tests for demo API routes."""
import pytest

import src.routes.demo_routes as demo_routes_module
from src.models import User


@pytest.fixture(autouse=True)
def reset_demo_user_cache():
    """Reset the module-level demo user PK cache before each test."""
    demo_routes_module._demo_user_pk = None
    yield
    demo_routes_module._demo_user_pk = None


@pytest.fixture
def demo_user(db_session):
    """Create a demo user in the test database."""
    user = User(user_id="demo", username="Demo User")
    user.set_password("demopass")
    db_session.add(user)
    db_session.commit()
    return user


# --- Fallback tests: demo user does NOT exist ---


class TestDemoFallbackNoUser:
    """Tests for fallback behavior when demo user does not exist."""

    def test_portfolio_summary_fallback(self, client, db_session):
        """GET /api/v1/demo/portfolio returns empty summary when no demo user."""
        resp = client.get("/api/v1/demo/portfolio")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert data["total_value"] == 0
        assert data["total_cost"] == 0
        assert data["total_unrealized_pnl"] == 0
        assert data["total_unrealized_pnl_percent"] == 0
        assert data["holdings_count"] == 0
        assert data["cash_balance"] == 0
        assert data["total_asset"] == 0

    def test_holdings_fallback(self, client, db_session):
        """GET /api/v1/demo/portfolio/holdings returns empty list when no demo user."""
        resp = client.get("/api/v1/demo/portfolio/holdings")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"] == []

    def test_valuation_history_fallback(self, client, db_session):
        """GET /api/v1/demo/portfolio/valuation-history returns empty list."""
        resp = client.get("/api/v1/demo/portfolio/valuation-history")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"] == []

    def test_favorites_fallback(self, client, db_session):
        """GET /api/v1/demo/favorites returns empty list when no demo user."""
        resp = client.get("/api/v1/demo/favorites")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"] == []

    def test_trades_fallback(self, client, db_session):
        """GET /api/v1/demo/trades returns empty list when no demo user."""
        resp = client.get("/api/v1/demo/trades")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"] == []

    def test_cash_flows_fallback(self, client, db_session):
        """GET /api/v1/demo/cash-flows returns empty list when no demo user."""
        resp = client.get("/api/v1/demo/cash-flows")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"] == []


# --- Normal tests: demo user exists (empty data) ---


class TestDemoWithUser:
    """Tests for normal behavior when demo user exists but has no data."""

    def test_portfolio_summary(self, client, db_session, demo_user):
        """GET /api/v1/demo/portfolio returns summary for demo user."""
        resp = client.get("/api/v1/demo/portfolio")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        # Demo user with no trades has zero values
        assert "total_value" in data
        assert "holdings_count" in data

    def test_holdings(self, client, db_session, demo_user):
        """GET /api/v1/demo/portfolio/holdings returns holdings list."""
        resp = client.get("/api/v1/demo/portfolio/holdings")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    def test_valuation_history(self, client, db_session, demo_user):
        """GET /api/v1/demo/portfolio/valuation-history returns history list."""
        resp = client.get("/api/v1/demo/portfolio/valuation-history")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    def test_valuation_history_period_param(self, client, db_session, demo_user):
        """GET /api/v1/demo/portfolio/valuation-history respects period param."""
        resp = client.get("/api/v1/demo/portfolio/valuation-history?period=3m")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True

    def test_valuation_history_invalid_period(self, client, db_session, demo_user):
        """Invalid period defaults to 1y."""
        resp = client.get("/api/v1/demo/portfolio/valuation-history?period=invalid")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True

    def test_favorites(self, client, db_session, demo_user):
        """GET /api/v1/demo/favorites returns favorites list."""
        resp = client.get("/api/v1/demo/favorites")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    def test_trades(self, client, db_session, demo_user):
        """GET /api/v1/demo/trades returns trades list."""
        resp = client.get("/api/v1/demo/trades")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    def test_cash_flows(self, client, db_session, demo_user):
        """GET /api/v1/demo/cash-flows returns cash flows list."""
        resp = client.get("/api/v1/demo/cash-flows")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
