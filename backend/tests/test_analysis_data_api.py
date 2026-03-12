"""Tests for GET /api/v1/portfolio/analysis-data endpoint."""
from datetime import date
from decimal import Decimal

import pytest

from src.models import (
    ETF,
    ETFTagRelation,
    PerformanceCache,
    PriceHistory,
    ScoreCache,
    Tag,
    Trade,
    User,
)


@pytest.fixture
def auth_user(db_session):
    """Create and return an authenticated user with holdings."""
    user = User(user_id="testuser", username="Test User")
    user.set_password("testpass")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_etf(db_session):
    """Create a sample ETF."""
    etf = ETF(code="1475", name="iシェアーズTOPIX ETF", type="ETF")
    db_session.add(etf)
    db_session.commit()
    return etf


@pytest.fixture
def sample_trade(db_session, auth_user, sample_etf):
    """Create a sample trade for the user."""
    trade = Trade(
        user_id=auth_user.id,
        etf_code="1475",
        trade_type="buy",
        quantity=100,
        price=Decimal("2000"),
        trade_date=date(2025, 1, 1),
    )
    db_session.add(trade)
    db_session.commit()
    return trade


@pytest.fixture
def sample_performance(db_session, sample_etf):
    """Create sample performance cache data."""
    perf = PerformanceCache(
        etf_code="1475",
        period="1y",
        return_rate=0.15,
        volatility=0.12,
        regression_rate=0.14,
    )
    db_session.add(perf)
    db_session.commit()
    return perf


@pytest.fixture
def sample_score(db_session, sample_etf):
    """Create sample score cache data."""
    score = ScoreCache(
        etf_code="1475",
        perspective="balance",
        total_score=76.4,
        dividend_power=80.0,
        cost_efficiency=72.0,
        scale_reliability=75.0,
        trading_quality=78.0,
        return_performance=77.0,
    )
    db_session.add(score)
    db_session.commit()
    return score


@pytest.fixture
def sample_tag(db_session, sample_etf):
    """Create sample tag data."""
    tag = Tag(name="TOPIX連動", color="#3B82F6", category="theme")
    db_session.add(tag)
    db_session.commit()
    relation = ETFTagRelation(etf_code="1475", tag_id=tag.id)
    db_session.add(relation)
    db_session.commit()
    return tag


@pytest.fixture
def sample_price(db_session, sample_etf):
    """Create sample price history data."""
    price = PriceHistory(
        etf_code="1475",
        date=date.today(),
        open=2140.0,
        high=2160.0,
        low=2130.0,
        close=2155.0,
        volume=15000,
    )
    db_session.add(price)
    db_session.commit()
    return price


def _login(client, user_id="testuser", password="testpass"):
    """Helper to log in."""
    return client.post(
        "/api/v1/auth/login",
        json={"user_id": user_id, "password": password},
    )


class TestAnalysisDataUnauthorized:
    """Tests for unauthorized access."""

    def test_requires_auth(self, client, db_session):
        """GET /api/v1/portfolio/analysis-data returns 401 without auth."""
        resp = client.get("/api/v1/portfolio/analysis-data")
        assert resp.status_code == 401


class TestAnalysisDataResponse:
    """Tests for response structure."""

    def test_returns_all_keys(
        self,
        client,
        db_session,
        auth_user,
        sample_trade,
        sample_performance,
        sample_score,
        sample_tag,
        sample_price,
    ):
        """Response contains all expected top-level keys."""
        _login(client)
        resp = client.get("/api/v1/portfolio/analysis-data")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        expected_keys = {
            "performance_cache",
            "score_cache",
            "etf_data",
            "tag_data",
            "price_data",
            "price_data_daily_30d",
            "price_data_close_250d",
        }
        assert expected_keys == set(data.keys())

    def test_performance_cache_fields(
        self,
        client,
        db_session,
        auth_user,
        sample_trade,
        sample_performance,
    ):
        """Performance cache items have correct fields."""
        _login(client)
        resp = client.get("/api/v1/portfolio/analysis-data")
        data = resp.get_json()["data"]
        assert len(data["performance_cache"]) == 1
        item = data["performance_cache"][0]
        assert item["etf_code"] == "1475"
        assert item["period"] == "1y"
        assert item["return_rate"] == 0.15
        assert item["volatility"] == 0.12

    def test_score_cache_fields(
        self,
        client,
        db_session,
        auth_user,
        sample_trade,
        sample_score,
    ):
        """Score cache items have correct fields."""
        _login(client)
        resp = client.get("/api/v1/portfolio/analysis-data")
        data = resp.get_json()["data"]
        assert len(data["score_cache"]) == 1
        item = data["score_cache"][0]
        assert item["etf_code"] == "1475"
        assert item["perspective"] == "balance"
        assert item["total_score"] == 76.4
        assert item["dividend_power"] == 80.0

    def test_etf_data_fields(
        self,
        client,
        db_session,
        auth_user,
        sample_trade,
    ):
        """ETF data items have correct fields."""
        _login(client)
        resp = client.get("/api/v1/portfolio/analysis-data")
        data = resp.get_json()["data"]
        assert len(data["etf_data"]) == 1
        item = data["etf_data"][0]
        assert item["code"] == "1475"
        assert "momentum_label" in item
        assert "manager" in item
        assert "listing_date" in item
        assert "deviation_rate" in item
        assert "expense_ratio" in item
        assert "dividend_yield" in item

    def test_tag_data_fields(
        self,
        client,
        db_session,
        auth_user,
        sample_trade,
        sample_tag,
    ):
        """Tag data items have correct fields."""
        _login(client)
        resp = client.get("/api/v1/portfolio/analysis-data")
        data = resp.get_json()["data"]
        assert len(data["tag_data"]) == 1
        item = data["tag_data"][0]
        assert item["etf_code"] == "1475"
        assert item["name"] == "TOPIX連動"
        assert item["category"] == "theme"

    def test_empty_holdings(self, client, db_session, auth_user):
        """Returns empty arrays when user has no holdings."""
        _login(client)
        resp = client.get("/api/v1/portfolio/analysis-data")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        for key in data:
            assert data[key] == []
