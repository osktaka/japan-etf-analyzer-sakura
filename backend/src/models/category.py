"""Category model for ETF categories."""
from . import db
from .base import TimestampMixin


class Category(TimestampMixin, db.Model):
    """ETF category (asset class) model."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    # Relationship
    etfs = db.relationship("ETF", back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "sort_order": self.sort_order,
        }
