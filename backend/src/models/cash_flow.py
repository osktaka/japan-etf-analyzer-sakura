"""CashFlow model for user's deposit/withdrawal transactions."""

from . import db
from .base import TimestampMixin


class CashFlow(db.Model, TimestampMixin):
    """User's cash deposit or withdrawal transaction."""

    __tablename__ = "cash_flows"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    flow_type = db.Column(db.String(10), nullable=False)  # 'deposit' or 'withdrawal'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    flow_date = db.Column(db.Date, nullable=False)
    memo = db.Column(db.Text, nullable=True)

    # Relationships
    user = db.relationship("User", back_populates="cash_flows")

    # Index for performance
    __table_args__ = (
        db.Index("ix_cash_flows_user_id", "user_id"),
        db.Index("ix_cash_flows_flow_date", "flow_date"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "flow_type": self.flow_type,
            "amount": float(self.amount) if self.amount else None,
            "flow_date": self.flow_date.isoformat() if self.flow_date else None,
            "memo": self.memo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<CashFlow id={self.id} user_id={self.user_id} "
            f"type={self.flow_type} amount={self.amount}>"
        )
