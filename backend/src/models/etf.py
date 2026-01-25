"""ETF model for ETF securities."""
from . import db
from .base import TimestampMixin


class ETF(TimestampMixin, db.Model):
    """ETF (Exchange Traded Fund) model."""

    __tablename__ = "etfs"

    code = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True
    )
    expense_ratio = db.Column(db.Numeric(5, 3), nullable=True)
    dividend_yield = db.Column(db.Numeric(5, 2), nullable=True)
    nav = db.Column(db.Numeric(12, 2), nullable=True)
    market_price = db.Column(db.Numeric(12, 2), nullable=True)
    deviation_rate = db.Column(db.Numeric(5, 2), nullable=True)
    total_assets = db.Column(db.Numeric(15, 0), nullable=True)
    listing_date = db.Column(db.Date, nullable=True)
    index_name = db.Column(db.String(100), nullable=True)
    manager = db.Column(db.String(100), nullable=True)

    # Relationships
    category = db.relationship("Category", back_populates="etfs")
    tag_relations = db.relationship(
        "ETFTagRelation",
        back_populates="etf",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Index
    __table_args__ = (db.Index("idx_etfs_name", "name"),)

    def __repr__(self):
        return f"<ETF {self.code}: {self.name}>"

    @property
    def tags(self):
        """Get all tags for this ETF."""
        return [relation.tag for relation in self.tag_relations]

    def to_dict(self, include_tags=True):
        """Convert to dictionary."""
        data = {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "expense_ratio": float(self.expense_ratio) if self.expense_ratio else None,
            "dividend_yield": (
                float(self.dividend_yield) if self.dividend_yield else None
            ),
            "nav": float(self.nav) if self.nav else None,
            "market_price": float(self.market_price) if self.market_price else None,
            "deviation_rate": (
                float(self.deviation_rate) if self.deviation_rate else None
            ),
            "total_assets": float(self.total_assets) if self.total_assets else None,
            "listing_date": (
                self.listing_date.isoformat() if self.listing_date else None
            ),
            "index_name": self.index_name,
            "manager": self.manager,
        }
        if include_tags:
            data["tags"] = [tag.to_dict() for tag in self.tags]
        return data

    def to_summary_dict(self):
        """Convert to summary dictionary (for list views)."""
        return {
            "code": self.code,
            "name": self.name,
            "category": self.category.name if self.category else None,
            "expense_ratio": float(self.expense_ratio) if self.expense_ratio else None,
            "dividend_yield": (
                float(self.dividend_yield) if self.dividend_yield else None
            ),
            "market_price": float(self.market_price) if self.market_price else None,
            "tags": [tag.to_dict() for tag in self.tags],
        }
