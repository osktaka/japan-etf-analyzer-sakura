"""Favorite model for user's favorite ETFs."""
from . import db
from .base import TimestampMixin


class Favorite(db.Model, TimestampMixin):
    """User's favorite ETF."""

    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    etf_code = db.Column(
        db.String(10), db.ForeignKey("etfs.code", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="favorites")
    etf = db.relationship("ETF", backref=db.backref("favorites", lazy="dynamic"))

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("user_id", "etf_code", name="uq_user_etf_favorite"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "etf_code": self.etf_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<Favorite user_id={self.user_id} etf_code={self.etf_code}>"
