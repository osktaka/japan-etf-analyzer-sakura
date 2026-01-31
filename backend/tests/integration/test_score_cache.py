"""Integration tests for score cache functionality."""
import pytest


def test_score_cache_repository_upsert(app, db_session):
    """Test score cache upsert operation."""
    from src.repositories import ScoreCacheRepository

    repo = ScoreCacheRepository()

    # First insert
    cache = repo.upsert(
        etf_code="1306",
        perspective="balance",
        total_score=85.5,
        axis_scores={
            "dividend_power": 55.7,
            "cost_efficiency": 98.3,
            "scale_reliability": 91.4,
            "trading_quality": 90.9,
            "return_performance": 78.6,
        },
    )

    assert cache is not None
    assert cache.etf_code == "1306"
    assert cache.perspective == "balance"
    assert cache.total_score == 85.5
    assert cache.dividend_power == 55.7

    # Update (upsert)
    updated = repo.upsert(
        etf_code="1306",
        perspective="balance",
        total_score=87.0,
        axis_scores={
            "dividend_power": 60.0,
            "cost_efficiency": 98.3,
            "scale_reliability": 91.4,
            "trading_quality": 90.9,
            "return_performance": 78.6,
        },
    )

    assert updated.total_score == 87.0
    assert updated.dividend_power == 60.0

    # Verify only one record exists
    all_caches = repo.get_by_code("1306")
    balance_caches = [c for c in all_caches if c.perspective == "balance"]
    assert len(balance_caches) == 1


def test_score_cache_batch_retrieval(app, db_session):
    """Test batch retrieval of score caches."""
    from src.repositories import ScoreCacheRepository

    repo = ScoreCacheRepository()

    # Insert multiple ETFs and perspectives
    test_data = [
        ("1306", "balance", 85.5),
        ("1306", "dividend", 90.0),
        ("1475", "balance", 88.0),
    ]

    for code, perspective, score in test_data:
        repo.upsert(
            etf_code=code,
            perspective=perspective,
            total_score=score,
            axis_scores={
                "dividend_power": 50.0,
                "cost_efficiency": 50.0,
                "scale_reliability": 50.0,
                "trading_quality": 50.0,
                "return_performance": 50.0,
            },
        )

    # Test get_all_perspectives_batch
    result = repo.get_all_perspectives_batch(["1306", "1475"])
    assert "1306" in result
    assert "1475" in result
    assert "balance" in result["1306"]
    assert "dividend" in result["1306"]
    assert result["1306"]["balance"].total_score == 85.5
    assert result["1306"]["dividend"].total_score == 90.0


def test_recommend_service_with_cache(app, db_session):
    """Test recommend service using score cache."""
    from src.repositories import ScoreCacheRepository, ETFRepository
    from src.services import RecommendService

    # Prepare test data
    score_repo = ScoreCacheRepository()
    etf_repo = ETFRepository()

    # Get a real ETF
    etfs = etf_repo.search(limit=1, offset=0)
    if not etfs:
        pytest.skip("No ETF data available in test database")
    etf = etfs[0]

    # Insert score cache
    score_repo.upsert(
        etf_code=etf.code,
        perspective="balance",
        total_score=95.0,
        axis_scores={
            "dividend_power": 90.0,
            "cost_efficiency": 95.0,
            "scale_reliability": 92.0,
            "trading_quality": 93.0,
            "return_performance": 88.0,
        },
    )

    # Get recommendations
    service = RecommendService()
    result = service.get_recommendations(perspective="balance", limit=5)

    assert "perspective" in result
    assert "items" in result
    assert len(result["items"]) > 0

    # Check if axis_scores are included
    first_item = result["items"][0]
    assert "axis_scores" in first_item
    assert "dividend_power" in first_item["axis_scores"]
    assert first_item["axis_scores"]["dividend_power"] is not None


def test_etf_service_batch_scores_cached(app, db_session):
    """Test ETF service batch scores using cache."""
    from src.repositories import ScoreCacheRepository, ETFRepository
    from src.services import ETFService

    # Prepare test data
    score_repo = ScoreCacheRepository()
    etf_repo = ETFRepository()

    # Get real ETFs
    etfs = etf_repo.search(limit=2, offset=0)
    if not etfs:
        pytest.skip("No ETF data available in test database")
    codes = [etf.code for etf in etfs]

    # Insert score caches
    for code in codes:
        for perspective in ["balance", "dividend"]:
            score_repo.upsert(
                etf_code=code,
                perspective=perspective,
                total_score=80.0,
                axis_scores={
                    "dividend_power": 75.0,
                    "cost_efficiency": 80.0,
                    "scale_reliability": 85.0,
                    "trading_quality": 75.0,
                    "return_performance": 80.0,
                },
            )

    # Get batch scores
    service = ETFService()
    result = service.get_batch_scores(codes)

    # Verify results
    assert len(result) == len(codes)
    for code in codes:
        assert code in result
        assert "balance" in result[code]
        assert "dividend" in result[code]
        assert result[code]["balance"] == 80.0
