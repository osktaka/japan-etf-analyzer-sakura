"""User model for authentication."""

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .base import TimestampMixin


class User(db.Model, UserMixin, TimestampMixin):
    """User model with Flask-Login support."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # Relationship to favorites
    favorites = db.relationship(
        "Favorite", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    # Relationship to trades
    trades = db.relationship(
        "Trade", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    # Relationship to cash flows
    cash_flows = db.relationship(
        "CashFlow", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        """Set hashed password."""
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": (
                self.created_at.isoformat() + "Z" if self.created_at else None
            ),
            "last_login_at": (
                self.last_login_at.isoformat() + "Z" if self.last_login_at else None
            ),
        }

    def __repr__(self) -> str:
        return f"<User {self.user_id}>"
