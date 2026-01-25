"""Price history model for caching ETF price data."""
from datetime import datetime

from . import db


class PriceHistory(db.Model):
    """Historical price data for ETFs (cache for Yahoo Finance data)."""

    __tablename__ = "price_histories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    etf_code = db.Column(db.String(10), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    open = db.Column(db.Float, nullable=True)
    high = db.Column(db.Float, nullable=True)
    low = db.Column(db.Float, nullable=True)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (db.UniqueConstraint("etf_code", "date", name="uq_etf_code_date"),)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
