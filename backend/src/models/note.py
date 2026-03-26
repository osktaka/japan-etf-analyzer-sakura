"""Note model for article management."""

from . import db
from .base import TimestampMixin


class Note(db.Model, TimestampMixin):
    """Article/note entity for published content."""

    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(200), nullable=False, unique=True)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="published")
    published_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.Index("ix_notes_status_published_at", "status", published_at.desc()),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary with all fields."""
        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "status": self.status,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }

    def to_list_dict(self) -> dict:
        """Convert to dictionary without content (for list views)."""
        result = self.to_dict()
        del result["content"]
        return result

    def __repr__(self) -> str:
        return f"<Note id={self.id} slug={self.slug} status={self.status}>"
