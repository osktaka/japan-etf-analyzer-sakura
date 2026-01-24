"""Tag model for ETF tags."""
from . import db
from .base import TimestampMixin


class Tag(TimestampMixin, db.Model):
    """Tag model for ETF classification."""

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), nullable=True, default="#6B7280")

    # Relationship
    etf_relations = db.relationship(
        "ETFTagRelation", back_populates="tag", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Tag {self.id}: {self.name}>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
        }
