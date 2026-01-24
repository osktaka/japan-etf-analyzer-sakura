"""Integration tests for API endpoints."""

from src.models import Category, ETF, ETFTagRelation, Tag


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json["status"] == "ok"


class TestCategoryEndpoints:
    """Tests for category endpoints."""

    def test_get_categories_empty(self, client, db_session):
        """Test getting categories when empty."""
        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        assert response.json["success"] is True
        assert response.json["data"] == []

    def test_get_categories(self, client, db_session):
        """Test getting categories."""
        db_session.add(Category(name="国内株式", sort_order=1))
        db_session.add(Category(name="外国株式", sort_order=2))
        db_session.commit()

        response = client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 2
        assert data[0]["name"] == "国内株式"

    def test_get_category_by_id(self, client, db_session):
        """Test getting category by ID."""
        category = Category(name="REIT", sort_order=5)
        db_session.add(category)
        db_session.commit()

        response = client.get(f"/api/v1/categories/{category.id}")
        assert response.status_code == 200
        assert response.json["data"]["name"] == "REIT"

    def test_get_category_not_found(self, client, db_session):
        """Test getting non-existent category."""
        response = client.get("/api/v1/categories/999")
        assert response.status_code == 404


class TestTagEndpoints:
    """Tests for tag endpoints."""

    def test_get_tags(self, client, db_session):
        """Test getting tags."""
        db_session.add(Tag(name="高配当", color="#10B981"))
        db_session.add(Tag(name="低コスト", color="#3B82F6"))
        db_session.commit()

        response = client.get("/api/v1/tags")
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 2


class TestETFEndpoints:
    """Tests for ETF endpoints."""

    def test_get_etfs_empty(self, client, db_session):
        """Test getting ETFs when empty."""
        response = client.get("/api/v1/etfs")
        assert response.status_code == 200
        assert response.json["data"] == []

    def test_get_etfs(self, client, db_session):
        """Test getting ETFs."""
        db_session.add(ETF(code="1306", name="TOPIX連動型"))
        db_session.add(ETF(code="1321", name="日経225連動型"))
        db_session.commit()

        response = client.get("/api/v1/etfs")
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 2

    def test_get_etfs_with_search(self, client, db_session):
        """Test searching ETFs by keyword."""
        db_session.add(ETF(code="1306", name="TOPIX連動型"))
        db_session.add(ETF(code="1321", name="日経225連動型"))
        db_session.commit()

        response = client.get("/api/v1/etfs?keyword=TOPIX")
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 1
        assert data[0]["code"] == "1306"

    def test_get_etf_by_code(self, client, db_session):
        """Test getting ETF by code."""
        db_session.add(ETF(code="1306", name="TOPIX連動型"))
        db_session.commit()

        response = client.get("/api/v1/etfs/1306")
        assert response.status_code == 200
        assert response.json["data"]["code"] == "1306"

    def test_get_etf_not_found(self, client, db_session):
        """Test getting non-existent ETF."""
        response = client.get("/api/v1/etfs/9999")
        assert response.status_code == 404

    def test_get_etf_chart(self, client, db_session):
        """Test getting ETF chart data."""
        db_session.add(ETF(code="1306", name="TOPIX連動型"))
        db_session.commit()

        response = client.get("/api/v1/etfs/1306/chart?period=1m")
        assert response.status_code == 200
        data = response.json["data"]
        assert data["code"] == "1306"
        assert data["period"] == "1m"
        assert len(data["data"]) > 0


class TestRecommendEndpoints:
    """Tests for recommendation endpoints."""

    def test_get_perspectives(self, client, db_session):
        """Test getting perspectives."""
        response = client.get("/api/v1/perspectives")
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 5
        perspective_ids = [p["id"] for p in data]
        assert "high-dividend" in perspective_ids
        assert "low-cost" in perspective_ids

    def test_get_recommendations(self, client, db_session):
        """Test getting recommendations."""
        tag = Tag(name="人気")
        db_session.add(tag)
        db_session.commit()

        etf = ETF(code="1306", name="TOPIX連動型")
        db_session.add(etf)
        db_session.commit()

        relation = ETFTagRelation(etf_code="1306", tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        response = client.get("/api/v1/recommendations?perspective=popular")
        assert response.status_code == 200
        data = response.json["data"]
        assert data["perspective"]["id"] == "popular"
        assert len(data["items"]) >= 0
