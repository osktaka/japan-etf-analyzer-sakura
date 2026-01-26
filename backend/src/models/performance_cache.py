"""Performance cache model for pre-calculated ETF returns."""
from datetime import datetime

from . import db


class PerformanceCache(db.Model):
    """Pre-calculated return rates for ETFs."""

    __tablename__ = "performance_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    etf_code = db.Column(db.String(10), nullable=False, index=True)
    period = db.Column(
        db.String(5), nullable=False
    )  # '1m','3m','6m','1y','3y','5y','10y','20y'
    return_rate = db.Column(db.Float, nullable=True)
    calculated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("etf_code", "period", name="uq_etf_code_period"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "etf_code": self.etf_code,
            "period": self.period,
            "return_rate": self.return_rate,
            "calculated_at": self.calculated_at.isoformat()
            if self.calculated_at
            else None,
        }
