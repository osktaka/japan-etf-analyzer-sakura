"""Public note API routes."""

from datetime import date

from flask import Blueprint, Response, request
from markupsafe import escape

from src.services.note_service import NoteService
from src.utils import api_response, error_response
from src.utils.decorators import api_key_required

SITE_URL = "https://kima3.net/japan-etf-analyzer"
STATIC_PAGES = ["/", "/compare", "/market", "/notes"]


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


def create_sitemap_bp():
    """Create sitemap blueprint."""
    bp = Blueprint("sitemap", __name__)
    service = NoteService()

    @bp.route("/sitemap.xml", methods=["GET"])
    def sitemap():
        """Generate sitemap.xml dynamically.

        GET /api/v1/sitemap.xml
        """
        today = date.today().isoformat()
        urls = []

        # Static pages
        for page in STATIC_PAGES:
            loc = f"{SITE_URL}{page}"
            urls.append(f"  <url>\n    <loc>{escape(loc)}</loc>"
                        f"\n    <lastmod>{today}</lastmod>\n  </url>")

        # Published notes
        notes = service.get_published_notes()
        for note in notes:
            slug = escape(note["slug"])
            lastmod = (note.get("updated_at")
                       or note.get("published_at")
                       or today)
            if hasattr(lastmod, "isoformat"):
                lastmod = lastmod.isoformat()
            # Extract date portion (YYYY-MM-DD) from ISO datetime
            lastmod = lastmod[:10]
            loc = f"{SITE_URL}/notes/{slug}"
            urls.append(f"  <url>\n    <loc>{escape(loc)}</loc>"
                        f"\n    <lastmod>{lastmod}</lastmod>\n  </url>")

        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "\n".join(urls) + "\n</urlset>")

        return Response(xml, content_type="application/xml")

    return bp
