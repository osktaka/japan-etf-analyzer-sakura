"""Public note API routes."""

import re
from datetime import date
from typing import Optional

from flask import Blueprint, Response, abort, request
from markupsafe import escape

from src.config.settings import Config
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


def _escape_html_attr(s: str) -> str:
    """Escape special characters for use in HTML attribute values."""
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inject_ogp(
    html: str,
    page_title: str,
    description: str,
    url: str,
    og_type: str = "article",
) -> str:
    """Inject OGP meta tags into base HTML."""
    safe_title = _escape_html_attr(page_title)
    safe_desc = _escape_html_attr(description)
    safe_url = _escape_html_attr(url)

    meta_tags = "\n    ".join(
        [
            f'<meta name="description" content="{safe_desc}" />',
            f'<meta property="og:title" content="{safe_title}" />',
            f'<meta property="og:description" content="{safe_desc}" />',
            f'<meta property="og:type" content="{og_type}" />',
            f'<meta property="og:url" content="{safe_url}" />',
            '<meta property="og:site_name" content="Japan ETF Analyzer" />',
            f'<link rel="canonical" href="{safe_url}" />',
        ]
    )

    result = re.sub(
        r"<title>[^<]*</title>", f"<title>{safe_title}</title>", html
    )
    result = result.replace("</head>", f"    {meta_tags}\n  </head>")
    return result


def _read_base_html() -> Optional[str]:
    """Read frontend/dist/index.html as OGP base template."""
    base_path = Config.BASE_DIR / "frontend" / "dist" / "index.html"
    if not base_path.exists():
        return None
    return base_path.read_text(encoding="utf-8")


def create_note_ogp_bp():
    """Create note OGP HTML blueprint."""
    bp = Blueprint("note_ogp", __name__)
    service = NoteService()

    @bp.route("/notes/<slug>.html")
    def note_ogp_html(slug: str):
        """Generate OGP-injected HTML for a note article.

        GET /api/v1/notes/<slug>.html
        """
        note = service.get_note_by_slug(slug)
        if not note:
            abort(404)

        base_html = _read_base_html()
        if not base_html:
            abort(500)

        title = f"{note['title']} - Japan ETF Analyzer"
        url = f"{SITE_URL}/notes/{slug}"
        html = _inject_ogp(base_html, title, note.get("summary", ""), url)
        return Response(html, content_type="text/html")

    @bp.route("/notes/index.html")
    def notes_list_ogp_html():
        """Generate OGP-injected HTML for the notes list page.

        GET /api/v1/notes/index.html
        """
        base_html = _read_base_html()
        if not base_html:
            abort(500)

        title = "ノート - Japan ETF Analyzer"
        description = "ETF投資に役立つ知識やコラムをまとめたノート一覧です。"
        url = f"{SITE_URL}/notes"
        html = _inject_ogp(base_html, title, description, url, "website")
        return Response(html, content_type="text/html")

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
