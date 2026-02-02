"""UserSettings model for storing custom weights."""

from . import db
from .base import TimestampMixin


class UserSettings(db.Model, TimestampMixin):
    """User settings model for custom weight configurations."""

    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    custom_weights = db.Column(db.Text, nullable=False)

    # Relationship to user
    user = db.relationship("User", backref=db.backref("settings", uselist=False))

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "custom_weights": self.custom_weights,
            "created_at": (
                self.created_at.isoformat() + "Z" if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() + "Z" if self.updated_at else None
            ),
        }

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id}>"
