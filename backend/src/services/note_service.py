"""Note service for article business logic."""

from datetime import datetime
from typing import Dict, List, Optional

from src.repositories.note_repository import NoteRepository


def _parse_datetime_fields(data: Dict) -> Dict:
    """Convert datetime string fields to datetime objects."""
    for field in ("published_at", "created_at", "updated_at"):
        if field in data and isinstance(data[field], str):
            try:
                data[field] = datetime.fromisoformat(data[field])
            except ValueError:
                raise ValueError(
                    f"{field}の日時形式が不正です: '{data[field]}'"
                    "（ISO 8601形式で指定してください 例: 2026-01-01T09:00:00）"
                )
    return data


class NoteService:
    """Service for note/article operations."""

    def __init__(self):
        """Initialize with note repository."""
        self.repo = NoteRepository()

    def get_published_notes(self) -> List[dict]:
        """Get all published notes (without content)."""
        notes = self.repo.get_published()
        return [note.to_list_dict() for note in notes]

    def get_note_by_slug(
        self, slug: str, include_unpublished: bool = False
    ) -> Optional[dict]:
        """Get a single note by slug."""
        note = self.repo.get_by_slug(slug)
        if not note:
            return None
        if not include_unpublished and note.status != "published":
            return None
        return note.to_dict()

    def create_note(self, data: Dict) -> dict:
        """Create a new note."""
        from src.models.note import Note

        data = _parse_datetime_fields(data)
        note = Note(**data)
        self.repo.create(note)
        return note.to_dict()

    def update_note(self, slug: str, data: Dict) -> Optional[dict]:
        """Update an existing note by slug."""
        note = self.repo.get_by_slug(slug)
        if not note:
            return None
        data = _parse_datetime_fields(data)
        for key, value in data.items():
            if hasattr(note, key):
                setattr(note, key, value)
        self.repo.save(note)
        return note.to_dict()

    def delete_note(self, slug: str) -> bool:
        """Delete a note by slug."""
        note = self.repo.get_by_slug(slug)
        if not note:
            return False
        self.repo.delete(note)
        return True

    def sync_note(self, data: Dict) -> dict:
        """Upsert a note by slug."""
        slug = data.pop("slug", None) or data.get("slug")
        if not slug:
            raise ValueError("slug is required for sync")
        data = _parse_datetime_fields(data)
        note = self.repo.upsert_by_slug(slug, data)
        return note.to_dict()
