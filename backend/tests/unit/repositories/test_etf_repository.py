"""Tests for ETFRepository."""
from decimal import Decimal

import pytest

from src.models import Category, ETF, ETFTagRelation, Tag
from src.repositories import ETFRepository


class TestETFRepository:
    """Test cases for ETFRepository."""

    def test_create_etf(self, db_session):
        """Test creating an ETF."""
        repo = ETFRepository()
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        result = repo.create(etf)

        assert result.code == "1306"
        assert result.name == "TOPIX連動型上場投資信託"

    def test_get_by_code(self, db_session):
        """Test getting ETF by code."""
        repo = ETFRepository()
        etf = ETF(code="1321", name="日経225連動型")
        repo.create(etf)

        result = repo.get_by_code("1321")

        assert result is not None
        assert result.name == "日経225連動型"

    def test_get_by_code_not_found(self, db_session):
        """Test getting non-existent ETF."""
        repo = ETFRepository()
        result = repo.get_by_code("9999")

        assert result is None

    def test_search_by_keyword(self, db_session):
        """Test searching ETFs by keyword."""
        repo = ETFRepository()
        repo.create(ETF(code="1306", name="TOPIX連動型上場投資信託"))
        repo.create(ETF(code="1321", name="日経225連動型"))
        repo.create(ETF(code="1343", name="REIT指数連動型"))

        results = repo.search(keyword="TOPIX")

        assert len(results) == 1
        assert results[0].code == "1306"

    def test_search_by_category(self, db_session):
        """Test searching ETFs by category."""
        category = Category(name="国内株式", sort_order=1)
        db_session.add(category)
        db_session.commit()

        repo = ETFRepository()
        repo.create(ETF(code="1306", name="TOPIX", category_id=category.id))
        repo.create(ETF(code="1343", name="REIT"))

        results = repo.search(category_id=category.id)

        assert len(results) == 1
        assert results[0].code == "1306"

    def test_search_by_dividend_yield(self, db_session):
        """Test searching ETFs by minimum dividend yield."""
        repo = ETFRepository()
        repo.create(ETF(code="1306", name="低配当", dividend_yield=Decimal("1.5")))
        repo.create(ETF(code="1489", name="高配当", dividend_yield=Decimal("4.5")))

        results = repo.search(min_dividend_yield=3.0)

        assert len(results) == 1
        assert results[0].code == "1489"

    def test_search_by_expense_ratio(self, db_session):
        """Test searching ETFs by max expense ratio."""
        repo = ETFRepository()
        repo.create(ETF(code="1306", name="低コスト", expense_ratio=Decimal("0.05")))
        repo.create(ETF(code="1489", name="高コスト", expense_ratio=Decimal("0.50")))

        results = repo.search(max_expense_ratio=0.1)

        assert len(results) == 1
        assert results[0].code == "1306"

    def test_get_high_dividend(self, db_session):
        """Test getting ETFs with highest dividend yield."""
        repo = ETFRepository()
        repo.create(ETF(code="1306", name="A", dividend_yield=Decimal("2.0")))
        repo.create(ETF(code="1489", name="B", dividend_yield=Decimal("4.0")))
        repo.create(ETF(code="1343", name="C", dividend_yield=Decimal("3.0")))

        results = repo.get_high_dividend(limit=2)

        assert len(results) == 2
        assert results[0].code == "1489"
        assert results[1].code == "1343"

    def test_get_low_cost(self, db_session):
        """Test getting ETFs with lowest expense ratio."""
        repo = ETFRepository()
        repo.create(ETF(code="1306", name="A", expense_ratio=Decimal("0.10")))
        repo.create(ETF(code="1489", name="B", expense_ratio=Decimal("0.05")))
        repo.create(ETF(code="1343", name="C", expense_ratio=Decimal("0.20")))

        results = repo.get_low_cost(limit=2)

        assert len(results) == 2
        assert results[0].code == "1489"
        assert results[1].code == "1306"

    def test_add_tag(self, db_session):
        """Test adding tag to ETF."""
        etf = ETF(code="1306", name="TOPIX")
        tag = Tag(name="人気")
        db_session.add_all([etf, tag])
        db_session.commit()

        repo = ETFRepository()
        result = repo.add_tag("1306", tag.id)

        assert result is not None
        assert result.etf_code == "1306"
        assert result.tag_id == tag.id

    def test_add_tag_duplicate(self, db_session):
        """Test adding same tag twice."""
        etf = ETF(code="1306", name="TOPIX")
        tag = Tag(name="人気")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation = ETFTagRelation(etf_code="1306", tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        repo = ETFRepository()
        result = repo.add_tag("1306", tag.id)

        assert result.id == relation.id

    def test_remove_tag(self, db_session):
        """Test removing tag from ETF."""
        etf = ETF(code="1306", name="TOPIX")
        tag = Tag(name="人気")
        db_session.add_all([etf, tag])
        db_session.commit()

        relation = ETFTagRelation(etf_code="1306", tag_id=tag.id)
        db_session.add(relation)
        db_session.commit()

        repo = ETFRepository()
        result = repo.remove_tag("1306", tag.id)

        assert result is True
        assert db_session.get(ETFTagRelation, relation.id) is None

    def test_create_or_update_new(self, db_session):
        """Test create_or_update with new ETF."""
        repo = ETFRepository()
        etf_data = {
            "code": "1306",
            "name": "TOPIX連動型",
            "expense_ratio": Decimal("0.066"),
        }

        result = repo.create_or_update(etf_data)

        assert result.code == "1306"
        assert result.name == "TOPIX連動型"
        assert float(result.expense_ratio) == 0.066

    def test_create_or_update_existing(self, db_session):
        """Test create_or_update with existing ETF."""
        etf = ETF(code="1306", name="旧名称", expense_ratio=Decimal("0.10"))
        db_session.add(etf)
        db_session.commit()

        repo = ETFRepository()
        etf_data = {
            "code": "1306",
            "name": "新名称",
            "expense_ratio": Decimal("0.05"),
        }

        result = repo.create_or_update(etf_data)

        assert result.name == "新名称"
        assert float(result.expense_ratio) == 0.05
