"""Integration tests for compare routes - /compare/scores endpoint."""
import pytest
from datetime import datetime

from src.models import ScoreCache


class TestCompareScores:
    """Test cases for GET /api/v1/compare/scores."""

    @pytest.fixture(autouse=True)
    def setup_score_cache(self, db_session):
        """Seed score cache data for tests."""
        entries = [
            ScoreCache(
                etf_code="1489",
                perspective="balance",
                total_score=65.0,
                total_score_full=72.5,
                dividend_power=80.0,
                cost_efficiency=60.0,
                scale_reliability=70.0,
                trading_quality=55.0,
                return_performance=75.0,
                calculated_at=datetime.utcnow(),
            ),
            ScoreCache(
                etf_code="1343",
                perspective="balance",
                total_score=58.0,
                total_score_full=64.0,
                dividend_power=50.0,
                cost_efficiency=90.0,
                scale_reliability=65.0,
                trading_quality=40.0,
                return_performance=60.0,
                calculated_at=datetime.utcnow(),
            ),
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

    def test_get_scores_success(self, client, db_session):
        """Normal case: codes=1489,1343&perspective=balance returns scores."""
        response = client.get(
            "/api/v1/compare/scores?codes=1489,1343&perspective=balance"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

        scores = data["data"]
        assert "1489" in scores
        assert "1343" in scores

        # Check 1489 scores
        assert scores["1489"]["score"] == 72.5  # total_score_full (full mode)
        assert scores["1489"]["axis_scores"]["dividend_power"] == 80.0
        assert scores["1489"]["axis_scores"]["cost_efficiency"] == 60.0
        assert scores["1489"]["axis_scores"]["scale_reliability"] == 70.0
        assert scores["1489"]["axis_scores"]["trading_quality"] == 55.0
        assert scores["1489"]["axis_scores"]["return_performance"] == 75.0

        # Check 1343 scores
        assert scores["1343"]["score"] == 64.0
        assert scores["1343"]["axis_scores"]["dividend_power"] == 50.0

    def test_get_scores_missing_codes_param(self, client, db_session):
        """Error case: no codes parameter returns 400."""
        response = client.get("/api/v1/compare/scores?perspective=balance")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_get_scores_empty_codes(self, client, db_session):
        """Error case: empty codes parameter returns 400."""
        response = client.get(
            "/api/v1/compare/scores?codes=&perspective=balance"
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_get_scores_too_many_codes(self, client, db_session):
        """Error case: more than 10 codes returns 400."""
        codes = ",".join([str(i) for i in range(1000, 1012)])  # 12 codes
        response = client.get(
            f"/api/v1/compare/scores?codes={codes}&perspective=balance"
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
