"""Score cache model for pre-calculated ETF scores."""
from datetime import datetime

from . import db


class ScoreCache(db.Model):
    """Pre-calculated evaluation scores for ETFs."""

    __tablename__ = "score_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    etf_code = db.Column(db.String(10), nullable=False, index=True)
    perspective = db.Column(
        db.String(20), nullable=False
    )  # 'dividend', 'low-cost', 'stability', 'volume', 'growth', 'balance'
    total_score = db.Column(db.Float, nullable=True)
    total_score_full = db.Column(db.Float, nullable=True)
    dividend_power = db.Column(db.Float, nullable=True)
    cost_efficiency = db.Column(db.Float, nullable=True)
    scale_reliability = db.Column(db.Float, nullable=True)
    trading_quality = db.Column(db.Float, nullable=True)
    return_performance = db.Column(db.Float, nullable=True)
    calculated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("etf_code", "perspective", name="uq_etf_code_perspective"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "etf_code": self.etf_code,
            "perspective": self.perspective,
            "total_score": self.total_score,
            "total_score_full": self.total_score_full,
            "axis_scores": {
                "dividend_power": self.dividend_power,
                "cost_efficiency": self.cost_efficiency,
                "scale_reliability": self.scale_reliability,
                "trading_quality": self.trading_quality,
                "return_performance": self.return_performance,
            },
            "calculated_at": self.calculated_at.isoformat()
            if self.calculated_at
            else None,
        }
