"""Trade model for user's ETF buy/sell transactions."""
from decimal import Decimal

from . import db
from .base import TimestampMixin


class Trade(db.Model, TimestampMixin):
    """User's ETF trade transaction."""

    __tablename__ = "trades"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    etf_code = db.Column(
        db.String(10), db.ForeignKey("etfs.code", ondelete="CASCADE"), nullable=False
    )
    trade_type = db.Column(db.String(4), nullable=False)  # 'buy' or 'sell'
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    trade_date = db.Column(db.Date, nullable=False)
    memo = db.Column(db.Text, nullable=True)

    # Relationships
    user = db.relationship("User", back_populates="trades")
    etf = db.relationship("ETF", backref=db.backref("trades", lazy="dynamic"))

    # Index for performance
    __table_args__ = (
        db.Index("ix_trades_user_id", "user_id"),
        db.Index("ix_trades_etf_code", "etf_code"),
        db.Index("ix_trades_trade_date", "trade_date"),
    )

    @property
    def total_amount(self) -> Decimal:
        """Calculate total transaction amount."""
        return Decimal(str(self.price)) * Decimal(str(self.quantity))

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "etf_code": self.etf_code,
            "trade_type": self.trade_type,
            "quantity": self.quantity,
            "price": float(self.price) if self.price else None,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "memo": self.memo,
            "total_amount": float(self.total_amount) if self.price else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<Trade id={self.id} user_id={self.user_id} etf_code={self.etf_code} "
            f"type={self.trade_type} qty={self.quantity}>"
        )
