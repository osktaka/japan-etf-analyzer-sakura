"""Stock split model for tracking ETF splits and reverse splits."""
from datetime import datetime

from . import db
from .base import TimestampMixin


class StockSplit(db.Model, TimestampMixin):
    """Stock split tracking model."""

    __tablename__ = "stock_splits"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    etf_code = db.Column(db.String(10), nullable=False, index=True)
    split_date = db.Column(db.Date, nullable=False, index=True)
    ratio = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    detected_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, nullable=True)
    previous_close = db.Column(db.Float, nullable=True)
    current_close = db.Column(db.Float, nullable=True)
    change_percent = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("etf_code", "split_date", name="uq_etf_code_split_date"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "etf_code": self.etf_code,
            "split_date": self.split_date.isoformat() if self.split_date else None,
            "ratio": self.ratio,
            "status": self.status,
            "detected_at": (
                self.detected_at.isoformat() + "Z" if self.detected_at else None
            ),
            "reviewed_at": (
                self.reviewed_at.isoformat() + "Z" if self.reviewed_at else None
            ),
            "reviewed_by": self.reviewed_by,
            "previous_close": self.previous_close,
            "current_close": self.current_close,
            "change_percent": self.change_percent,
            "created_at": (
                self.created_at.isoformat() + "Z" if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() + "Z" if self.updated_at else None
            ),
        }

    def __repr__(self) -> str:
        return f"<StockSplit {self.etf_code} {self.split_date} ratio={self.ratio}>"
