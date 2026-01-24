"""Tests for ETF model."""
from datetime import date
from decimal import Decimal

import pytest

from src.models import Category, ETF, ETFTagRelation, Tag


class TestETF:
    """Test cases for ETF model."""

    def test_create_etf(self, db_session):
        """Test creating an ETF."""
        etf = ETF(
            code="1306",
            name="TOPIX連動型上場投資信託",
            description="TOPIXに連動する国内株式ETF",
            expense_ratio=Decimal("0.066"),
            dividend_yield=Decimal("2.10"),
            nav=Decimal("2500.00"),
            market_price=Decimal("2505.00"),
            deviation_rate=Decimal("0.20"),
            total_assets=Decimal("15000000000000"),
            listing_date=date(2001, 7, 13),
        )
        db_session.add(etf)
        db_session.commit()

        assert etf.code == "1306"
        assert etf.name == "TOPIX連動型上場投資信託"
        assert float(etf.expense_ratio) == 0.066
        assert etf.created_at is not None

    def test_etf_with_category(self, db_session):
        """Test ETF with category relationship."""
        category = Category(name="国内株式", sort_order=1)
        db_session.add(category)
        db_session.commit()

        etf = ETF(
            code="1306",
            name="TOPIX連動型上場投資信託",
            category_id=category.id,
        )
        db_session.add(etf)
        db_session.commit()

        assert etf.category is not None
        assert etf.category.name == "国内株式"

    def test_etf_with_tags(self, db_session):
        """Test ETF with tags relationship."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        tag1 = Tag(name="高配当")
        tag2 = Tag(name="低コスト")
        db_session.add_all([etf, tag1, tag2])
        db_session.commit()

        relation1 = ETFTagRelation(etf_code=etf.code, tag_id=tag1.id)
        relation2 = ETFTagRelation(etf_code=etf.code, tag_id=tag2.id)
        db_session.add_all([relation1, relation2])
        db_session.commit()

        tags = etf.tags
        assert len(tags) == 2
        tag_names = [t.name for t in tags]
        assert "高配当" in tag_names
        assert "低コスト" in tag_names

    def test_etf_repr(self, db_session):
        """Test ETF string representation."""
        etf = ETF(code="1306", name="TOPIX連動型上場投資信託")
        db_session.add(etf)
        db_session.commit()

        assert "1306" in repr(etf)
        assert "TOPIX連動型上場投資信託" in repr(etf)

    def test_etf_to_dict(self, db_session):
        """Test converting ETF to dictionary."""
        category = Category(name="国内株式", sort_order=1)
        db_session.add(category)
        db_session.commit()

        etf = ETF(
            code="1306",
            name="TOPIX連動型上場投資信託",
            category_id=category.id,
            expense_ratio=Decimal("0.066"),
            dividend_yield=Decimal("2.10"),
            market_price=Decimal("2505.00"),
        )
        db_session.add(etf)
        db_session.commit()

        data = etf.to_dict()

        assert data["code"] == "1306"
        assert data["name"] == "TOPIX連動型上場投資信託"
        assert data["category"]["name"] == "国内株式"
        assert data["expense_ratio"] == 0.066
        assert data["dividend_yield"] == 2.10
        assert data["tags"] == []

    def test_etf_to_summary_dict(self, db_session):
        """Test converting ETF to summary dictionary."""
        category = Category(name="国内株式", sort_order=1)
        db_session.add(category)
        db_session.commit()

        etf = ETF(
            code="1306",
            name="TOPIX連動型上場投資信託",
            category_id=category.id,
            expense_ratio=Decimal("0.066"),
            dividend_yield=Decimal("2.10"),
            market_price=Decimal("2505.00"),
        )
        db_session.add(etf)
        db_session.commit()

        data = etf.to_summary_dict()

        assert data["code"] == "1306"
        assert data["category"] == "国内株式"
        assert "description" not in data
        assert "nav" not in data
