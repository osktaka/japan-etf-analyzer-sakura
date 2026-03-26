"""Public note API routes."""

from flask import Blueprint, request

from src.services.note_service import NoteService
from src.utils import api_response, error_response
from src.utils.decorators import api_key_required


def create_note_bp():
    """Create note blueprint."""
    bp = Blueprint("notes", __name__, url_prefix="/notes")
    service = NoteService()

    @bp.route("", methods=["GET"])
    def get_notes():
        """Get published notes list (without content).

        GET /api/v1/notes
        """
        notes = service.get_published_notes()
        return api_response(data=notes)

    @bp.route("/<slug>", methods=["GET"])
    def get_note(slug: str):
        """Get a single note by slug.

        GET /api/v1/notes/<slug>
        """
        note = service.get_note_by_slug(slug)
        if not note:
            return error_response("記事が見つかりません", 404)
        return api_response(data=note)

    @bp.route("/sync", methods=["POST"])
    @api_key_required
    def sync_note():
        """Upsert a note via API key authentication.

        POST /api/v1/notes/sync
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

        note = service.sync_note(data)
        return api_response(data=note, message="記事を同期しました")

    return bp
