"""Base model with common fields."""
from datetime import datetime

from . import db


class TimestampMixin:
    """Mixin for created_at and updated_at fields."""

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
