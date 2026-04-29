"""MechanicalRuleEvent model for tracking advisor rule triggers."""

from . import db
from .base import TimestampMixin


class MechanicalRuleEvent(db.Model, TimestampMixin):
    """機械ルール発動イベント.

    fingerprint で同日同銘柄同ルールの重複を抑止する.
    """

    __tablename__ = "mechanical_rule_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fingerprint = db.Column(db.String(128), nullable=False, unique=True, index=True)
    occurred_on = db.Column(db.Date, nullable=False, index=True)
    rule_kind = db.Column(db.String(50), nullable=False, index=True)
    etf_code = db.Column(db.String(20), nullable=True, index=True)
    user_id = db.Column(db.String(50), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default="info")
    payload_json = db.Column(db.Text, nullable=True)
    notified = db.Column(db.Boolean, nullable=False, default=False)
    notified_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fingerprint": self.fingerprint,
            "occurred_on": self.occurred_on.isoformat() if self.occurred_on else None,
            "rule_kind": self.rule_kind,
            "etf_code": self.etf_code,
            "user_id": self.user_id,
            "severity": self.severity,
            "payload_json": self.payload_json,
            "notified": self.notified,
            "notified_at": (
                self.notified_at.isoformat() if self.notified_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<MechanicalRuleEvent {self.rule_kind} {self.etf_code} "
            f"@{self.occurred_on}>"
        )
