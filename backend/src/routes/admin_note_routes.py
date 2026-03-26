"""Admin note API routes."""

from flask import Blueprint, request
from flask_login import login_required

from src.services.note_service import NoteService
from src.utils import api_response, error_response
from src.utils.decorators import admin_required


def create_admin_note_bp():
    """Create admin note blueprint."""
    bp = Blueprint("admin_notes", __name__, url_prefix="/admin/notes")
    service = NoteService()

    @bp.route("", methods=["GET"])
    @login_required
    @admin_required
    def get_all_notes():
        """Get all notes including drafts.

        GET /api/v1/admin/notes
        """
        from src.repositories.note_repository import NoteRepository

        repo = NoteRepository()
        notes = repo.get_all_with_drafts()
        return api_response(data=[n.to_list_dict() for n in notes])

    @bp.route("/<slug>", methods=["GET"])
    @login_required
    @admin_required
    def get_note(slug: str):
        """Get a single note by slug (including drafts).

        GET /api/v1/admin/notes/<slug>
        """
        note = service.get_note_by_slug(slug, include_unpublished=True)
        if not note:
            return error_response("記事が見つかりません", 404)
        return api_response(data=note)

    @bp.route("", methods=["POST"])
    @login_required
    @admin_required
    def create_note():
        """Create a new note.

        POST /api/v1/admin/notes
        """
        data = request.get_json()
        if not data:
            return error_response("リクエストボディが必要です", 400)

        required = ["slug", "title", "summary", "content", "published_at"]
        missing = [f for f in required if f not in data]
        if missing:
            return error_response(f"必須フィールドが不足: {', '.join(missing)}", 400)

        # バリデーション
        if not data.get("slug", "").strip():
            return error_response("slugは空にできません", 400)
        if not data.get("title", "").strip():
            return error_response("titleは空にできません", 400)
        if data.get("status") and data["status"] not in ("published", "draft"):
            return error_response(
                "statusはpublishedまたはdraftのみ有効です", 400
            )

        note = service.create_note(data)
        return api_response(data=note, message="記事を作成しました", status_code=201)

    @bp.route("/<slug>", methods=["PUT"])
    @login_required
    @admin_required
    def update_note(slug: str):
        """Update an existing note.

        PUT /api/v1/admin/notes/<slug>
        """
        data = request.get_json()
        if not data:
            return error_response("リクエストボディが必要です", 400)

        # バリデーション
        if "slug" in data and not data["slug"].strip():
            return error_response("slugは空にできません", 400)
        if "title" in data and not data["title"].strip():
            return error_response("titleは空にできません", 400)
        if "status" in data and data["status"] not in ("published", "draft"):
            return error_response(
                "statusはpublishedまたはdraftのみ有効です", 400
            )

        note = service.update_note(slug, data)
        if not note:
            return error_response("記事が見つかりません", 404)
        return api_response(data=note, message="記事を更新しました")

    @bp.route("/<slug>", methods=["DELETE"])
    @login_required
    @admin_required
    def delete_note(slug: str):
        """Delete a note.

        DELETE /api/v1/admin/notes/<slug>
        """
        deleted = service.delete_note(slug)
        if not deleted:
            return error_response("記事が見つかりません", 404)
        return api_response(message="記事を削除しました")

    return bp
