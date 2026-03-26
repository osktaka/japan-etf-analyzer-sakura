"""Note repository for database operations."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.exc import IntegrityError

from src.models import db
from src.models.note import Note

from .base_repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository for Note entity."""

    model = Note

    def get_by_slug(self, slug: str) -> Optional[Note]:
        """Get a note by its slug."""
        return db.session.query(Note).filter(Note.slug == slug).first()

    def get_published(self) -> List[Note]:
        """Get published notes ordered by published_at desc."""
        now = datetime.utcnow()
        return (
            db.session.query(Note)
            .filter(Note.status == "published", Note.published_at <= now)
            .order_by(Note.published_at.desc())
            .all()
        )

    def get_all_with_drafts(self) -> List[Note]:
        """Get all notes including drafts, ordered by published_at desc."""
        return (
            db.session.query(Note)
            .order_by(Note.published_at.desc())
            .all()
        )

    def upsert_by_slug(self, slug: str, data: Dict) -> Note:
        """Create or update a note by slug."""
        note = self.get_by_slug(slug)
        if note:
            for key, value in data.items():
                if hasattr(note, key):
                    setattr(note, key, value)
            note.updated_at = datetime.utcnow()
            db.session.commit()
            return note

        # 新規作成（並行アクセス時のIntegrityErrorに対応）
        try:
            data["slug"] = slug
            note = Note(**data)
            db.session.add(note)
            db.session.commit()
            return note
        except IntegrityError:
            db.session.rollback()
            # 並行アクセスで既に作成されていた場合、更新にフォールバック
            note = self.get_by_slug(slug)
            if note:
                for key, value in data.items():
                    if key != "slug" and hasattr(note, key):
                        setattr(note, key, value)
                note.updated_at = datetime.utcnow()
                db.session.commit()
                return note
            raise
