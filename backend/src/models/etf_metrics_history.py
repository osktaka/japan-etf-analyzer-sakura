"""ETF metrics history model for tracking daily evaluation metrics."""
from datetime import datetime

from . import db


class EtfMetricsHistory(db.Model):
    """Historical daily metrics data for ETF evaluation scores."""

    __tablename__ = "etf_metrics_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    etf_code = db.Column(db.String(10), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    dividend_yield = db.Column(db.Numeric(5, 2), nullable=True)
    expense_ratio = db.Column(db.Numeric(5, 3), nullable=True)
    total_assets = db.Column(db.Numeric(15, 0), nullable=True)
    deviation_rate = db.Column(db.Numeric(5, 2), nullable=True)
    return_1y = db.Column(db.Float, nullable=True)
    return_3y = db.Column(db.Float, nullable=True)
    volatility = db.Column(db.Float, nullable=True)
    momentum_label = db.Column(db.Text, nullable=True)
    regression_rate_1m = db.Column(db.Float, nullable=True)
    regression_rate_3m = db.Column(db.Float, nullable=True)
    regression_rate_6m = db.Column(db.Float, nullable=True)
    regression_rate_1y = db.Column(db.Float, nullable=True)
    regression_rate_3y = db.Column(db.Float, nullable=True)
    regression_rate_5y = db.Column(db.Float, nullable=True)
    regression_rate_10y = db.Column(db.Float, nullable=True)
    regression_rate_20y = db.Column(db.Float, nullable=True)
    return_rate_1m = db.Column(db.Float, nullable=True)
    return_rate_3m = db.Column(db.Float, nullable=True)
    return_rate_6m = db.Column(db.Float, nullable=True)
    return_rate_1y = db.Column(db.Float, nullable=True)
    return_rate_3y = db.Column(db.Float, nullable=True)
    return_rate_5y = db.Column(db.Float, nullable=True)
    return_rate_10y = db.Column(db.Float, nullable=True)
    return_rate_20y = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("etf_code", "date", name="uq_metrics_etf_code_date"),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "etf_code": self.etf_code,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "dividend_yield": (
                float(self.dividend_yield) if self.dividend_yield else None
            ),
            "expense_ratio": (
                float(self.expense_ratio) if self.expense_ratio else None
            ),
            "total_assets": float(self.total_assets) if self.total_assets else None,
            "deviation_rate": (
                float(self.deviation_rate) if self.deviation_rate else None
            ),
            "return_1y": self.return_1y,
            "return_3y": self.return_3y,
            "volatility": self.volatility,
            "momentum_label": self.momentum_label,
            "regression_rate_1m": self.regression_rate_1m,
            "regression_rate_3m": self.regression_rate_3m,
            "regression_rate_6m": self.regression_rate_6m,
            "regression_rate_1y": self.regression_rate_1y,
            "regression_rate_3y": self.regression_rate_3y,
            "regression_rate_5y": self.regression_rate_5y,
            "regression_rate_10y": self.regression_rate_10y,
            "regression_rate_20y": self.regression_rate_20y,
            "return_rate_1m": self.return_rate_1m,
            "return_rate_3m": self.return_rate_3m,
            "return_rate_6m": self.return_rate_6m,
            "return_rate_1y": self.return_rate_1y,
            "return_rate_3y": self.return_rate_3y,
            "return_rate_5y": self.return_rate_5y,
            "return_rate_10y": self.return_rate_10y,
            "return_rate_20y": self.return_rate_20y,
            "created_at": (self.created_at.isoformat() if self.created_at else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
        }
