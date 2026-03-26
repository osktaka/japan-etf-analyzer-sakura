"""Tests for admin note API routes."""

import pytest

from src.models import User, db
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


def _create_admin_user(session):
    """Create an admin user and return it."""
    user = User(user_id="admin", username="Admin User", is_admin=True)
    user.set_password("adminpass")
    session.add(user)
    session.commit()
    return user


def _create_regular_user(session):
    """Create a regular (non-admin) user and return it."""
    user = User(user_id="regular", username="Regular User", is_admin=False)
    user.set_password("regularpass")
    session.add(user)
    session.commit()
    return user


def _login(client, user_id, password):
    """Log in via the auth API."""
    return client.post(
        "/api/v1/auth/login",
        json={"user_id": user_id, "password": password},
    )


class TestAdminGetNotes:
    """Tests for GET /api/v1/admin/notes."""

    def test_returns_all_notes_including_drafts(self, client, app):
        """Admin GET returns both published and draft notes."""
        with app.app_context():
            _create_admin_user(db.session)
            _create_note(db.session, slug="pub", status="published")
            _create_note(db.session, slug="dft", status="draft")

        _login(client, "admin", "adminpass")
        resp = client.get("/api/v1/admin/notes")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["data"]) == 2

    def test_requires_authentication(self, client):
        """GET /api/v1/admin/notes returns 401 without login."""
        resp = client.get("/api/v1/admin/notes")
        assert resp.status_code == 401

    def test_requires_admin(self, client, app):
        """GET /api/v1/admin/notes returns 403 for non-admin."""
        with app.app_context():
            _create_regular_user(db.session)

        _login(client, "regular", "regularpass")
        resp = client.get("/api/v1/admin/notes")
        assert resp.status_code == 403


class TestAdminCreateNote:
    """Tests for POST /api/v1/admin/notes."""

    def test_creates_note(self, client, app):
        """Admin POST creates a new note."""
        with app.app_context():
            _create_admin_user(db.session)

        _login(client, "admin", "adminpass")
        resp = client.post(
            "/api/v1/admin/notes",
            json={
                "slug": "new-note",
                "title": "New Note",
                "summary": "Summary",
                "content": "Content",
                "published_at": "2026-01-01T00:00:00",
            },
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["data"]["slug"] == "new-note"

    def test_requires_fields(self, client, app):
        """Admin POST returns 400 for missing required fields."""
        with app.app_context():
            _create_admin_user(db.session)

        _login(client, "admin", "adminpass")
        resp = client.post(
            "/api/v1/admin/notes",
            json={"slug": "x"},
        )
        assert resp.status_code == 400


class TestAdminUpdateNote:
    """Tests for PUT /api/v1/admin/notes/<slug>."""

    def test_updates_note(self, client, app):
        """Admin PUT updates an existing note."""
        with app.app_context():
            _create_admin_user(db.session)
            _create_note(db.session, slug="update-me", title="Old")

        _login(client, "admin", "adminpass")
        resp = client.put(
            "/api/v1/admin/notes/update-me",
            json={"title": "New Title"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["data"]["title"] == "New Title"

    def test_returns_404_for_missing(self, client, app):
        """Admin PUT returns 404 for nonexistent slug."""
        with app.app_context():
            _create_admin_user(db.session)

        _login(client, "admin", "adminpass")
        resp = client.put(
            "/api/v1/admin/notes/nonexistent",
            json={"title": "X"},
        )
        assert resp.status_code == 404


class TestAdminDeleteNote:
    """Tests for DELETE /api/v1/admin/notes/<slug>."""

    def test_deletes_note(self, client, app):
        """Admin DELETE removes a note."""
        with app.app_context():
            _create_admin_user(db.session)
            _create_note(db.session, slug="delete-me")

        _login(client, "admin", "adminpass")
        resp = client.delete("/api/v1/admin/notes/delete-me")
        assert resp.status_code == 200

        # Verify deleted
        resp2 = client.get("/api/v1/notes/delete-me")
        assert resp2.status_code == 404

    def test_returns_404_for_missing(self, client, app):
        """Admin DELETE returns 404 for nonexistent slug."""
        with app.app_context():
            _create_admin_user(db.session)

        _login(client, "admin", "adminpass")
        resp = client.delete("/api/v1/admin/notes/nonexistent")
        assert resp.status_code == 404
