"""Tests for public note API routes."""

import os

import pytest

from src.models import db
from src.models.note import Note


@pytest.fixture(autouse=True)
def setup_db(app):
    """Set up database for each test."""
    with app.app_context():
        db.create_all()
        yield
        db.session.rollback()
        db.drop_all()


def _create_note(session, slug="test-note", status="published", **kwargs):
    """Helper to create a note in the database."""
    from datetime import datetime

    defaults = {
        "slug": slug,
        "title": "Test Note",
        "summary": "Test summary",
        "content": "Test content body",
        "status": status,
        "published_at": datetime(2026, 1, 1),
    }
    defaults.update(kwargs)
    note = Note(**defaults)
    session.add(note)
    session.commit()
    return note


class TestGetNotes:
    """Tests for GET /api/v1/notes."""

    def test_returns_empty_list(self, client):
        """GET /api/v1/notes returns empty array when no notes."""
        resp = client.get("/api/v1/notes")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"] == []

    def test_returns_published_notes_only(self, client, app):
        """GET /api/v1/notes excludes draft notes."""
        with app.app_context():
            _create_note(db.session, slug="published-note", status="published")
            _create_note(db.session, slug="draft-note", status="draft")

        resp = client.get("/api/v1/notes")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 1
        assert body["data"][0]["slug"] == "published-note"

    def test_list_excludes_content(self, client, app):
        """GET /api/v1/notes does not include content field."""
        with app.app_context():
            _create_note(db.session)

        resp = client.get("/api/v1/notes")
        body = resp.get_json()
        assert "content" not in body["data"][0]


class TestGetNoteBySlug:
    """Tests for GET /api/v1/notes/<slug>."""

    def test_returns_note_detail(self, client, app):
        """GET /api/v1/notes/<slug> returns note with content."""
        with app.app_context():
            _create_note(db.session, slug="my-article")

        resp = client.get("/api/v1/notes/my-article")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["data"]["slug"] == "my-article"
        assert "content" in body["data"]

    def test_returns_404_for_missing(self, client):
        """GET /api/v1/notes/<slug> returns 404 for nonexistent slug."""
        resp = client.get("/api/v1/notes/nonexistent")
        assert resp.status_code == 404

    def test_returns_404_for_draft(self, client, app):
        """GET /api/v1/notes/<slug> returns 404 for draft notes."""
        with app.app_context():
            _create_note(db.session, slug="draft-note", status="draft")

        resp = client.get("/api/v1/notes/draft-note")
        assert resp.status_code == 404


class TestSyncNote:
    """Tests for POST /api/v1/notes/sync."""

    def test_requires_api_key(self, client):
        """POST /api/v1/notes/sync returns 403 without API key."""
        resp = client.post(
            "/api/v1/notes/sync",
            json={"slug": "test", "title": "T", "summary": "S",
                  "content": "C", "published_at": "2026-01-01T00:00:00"},
        )
        assert resp.status_code == 403

    def test_creates_note_with_api_key(self, client, app):
        """POST /api/v1/notes/sync creates note with valid API key."""
        os.environ["NOTES_API_KEY"] = "test-key-123"
        try:
            resp = client.post(
                "/api/v1/notes/sync",
                json={
                    "slug": "new-article",
                    "title": "New Article",
                    "summary": "Summary",
                    "content": "Content body",
                    "published_at": "2026-01-01T00:00:00",
                },
                headers={"Authorization": "Bearer test-key-123"},
            )
            assert resp.status_code == 200
            body = resp.get_json()
            assert body["success"] is True
            assert body["data"]["slug"] == "new-article"
        finally:
            os.environ.pop("NOTES_API_KEY", None)

    def test_upserts_existing_note(self, client, app):
        """POST /api/v1/notes/sync updates existing note."""
        os.environ["NOTES_API_KEY"] = "test-key-123"
        try:
            with app.app_context():
                _create_note(db.session, slug="existing", title="Old Title")

            resp = client.post(
                "/api/v1/notes/sync",
                json={
                    "slug": "existing",
                    "title": "New Title",
                    "summary": "S",
                    "content": "C",
                    "published_at": "2026-01-01T00:00:00",
                },
                headers={"Authorization": "Bearer test-key-123"},
            )
            assert resp.status_code == 200
            assert resp.get_json()["data"]["title"] == "New Title"
        finally:
            os.environ.pop("NOTES_API_KEY", None)

    def test_rejects_invalid_api_key(self, client):
        """POST /api/v1/notes/sync returns 403 with wrong API key."""
        os.environ["NOTES_API_KEY"] = "correct-key"
        try:
            resp = client.post(
                "/api/v1/notes/sync",
                json={"slug": "t", "title": "T", "summary": "S",
                      "content": "C", "published_at": "2026-01-01T00:00:00"},
                headers={"Authorization": "Bearer wrong-key"},
            )
            assert resp.status_code == 403
        finally:
            os.environ.pop("NOTES_API_KEY", None)
