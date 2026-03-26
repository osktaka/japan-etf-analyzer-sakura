"""Publish a Markdown note to DB (and optionally sync to production)."""
import argparse
import os
import re
import sys
from pathlib import Path

# プロジェクトルートを特定（backend/scripts/ → backend/ → project root）
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 環境変数設定（本番環境用）
os.environ.setdefault("APP_BASE_DIR", str(PROJECT_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(PROJECT_ROOT / "data"))
db_path = PROJECT_ROOT / "data" / "etf.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

sys.path.insert(0, str(BACKEND_DIR))

# ベースディレクトリ（Docker: /app = CWD, 本番: PROJECT_ROOT）
# Docker内ではPROJECT_ROOTが/になるため、CWDを使用
BASE_DIR = Path.cwd() if str(PROJECT_ROOT) == "/" else PROJECT_ROOT


def parse_frontmatter(text: str) -> tuple:
    """Parse YAML frontmatter and body from Markdown text.

    Returns (metadata_dict, body_str).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError("frontmatterが見つかりません（---で囲まれたYAMLヘッダーが必要）")

    raw_yaml = match.group(1)
    body = match.group(2).strip()

    metadata = {}
    for line in raw_yaml.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        colon_idx = line.find(":")
        if colon_idx == -1:
            continue
        key = line[:colon_idx].strip()
        value = line[colon_idx + 1 :].strip()
        metadata[key] = value

    return metadata, body


def extract_slug(filepath: Path) -> str:
    """Extract slug from filename (remove .md extension)."""
    return filepath.stem


def escape_html_attr(s: str) -> str:
    """Escape special characters for use in HTML attribute values."""
    return (
        s.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate_ogp_html(slug: str, title: str, summary: str) -> None:
    """Generate OGP-injected HTML files for the note and notes index.

    Reads frontend/dist/index.html as the base template, injects OGP meta
    tags, and writes to frontend/dist/notes/{slug}.html.
    Also regenerates frontend/dist/notes/index.html for the notes list page.
    """
    site_url = "https://kima3.net/japan-etf-analyzer"
    dist_dir = BASE_DIR / "frontend" / "dist"
    base_html_path = dist_dir / "index.html"

    if not base_html_path.exists():
        print(f"Warning: {base_html_path} が存在しないためOGP HTML生成をスキップ")
        return

    base_html = base_html_path.read_text(encoding="utf-8")

    # notes出力ディレクトリ作成
    notes_out_dir = dist_dir / "notes"
    notes_out_dir.mkdir(parents=True, exist_ok=True)

    def inject_ogp(
        html: str,
        page_title: str,
        description: str,
        url: str,
        og_type: str = "article",
    ) -> str:
        safe_title = escape_html_attr(page_title)
        safe_desc = escape_html_attr(description)
        safe_url = escape_html_attr(url)

        meta_tags = "\n    ".join(
            [
                f'<meta name="description" content="{safe_desc}" />',
                f'<meta property="og:title" content="{safe_title}" />',
                f'<meta property="og:description" content="{safe_desc}" />',
                f'<meta property="og:type" content="{og_type}" />',
                f'<meta property="og:url" content="{safe_url}" />',
                f'<meta property="og:site_name" content="Japan ETF Analyzer" />',
                f'<link rel="canonical" href="{safe_url}" />',
            ]
        )

        # <title>タグを置換
        result = re.sub(r"<title>[^<]*</title>", f"<title>{safe_title}</title>", html)
        # </head>の直前にメタタグを注入
        result = result.replace("</head>", f"    {meta_tags}\n  </head>")
        return result

    # 個別ノート記事のOGP HTML生成
    page_title = f"{title} - Japan ETF Analyzer"
    url = f"{site_url}/notes/{slug}"
    html = inject_ogp(base_html, page_title, summary, url)
    out_path = notes_out_dir / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"OGP HTML生成: {out_path}")

    # ノート一覧ページ用プリレンダーHTML生成
    list_title = "ノート - Japan ETF Analyzer"
    list_desc = "ETF投資に役立つ知識やコラムをまとめたノート一覧です。"
    list_url = f"{site_url}/notes"
    list_html = inject_ogp(base_html, list_title, list_desc, list_url, "website")
    list_out_path = notes_out_dir / "index.html"
    list_out_path.write_text(list_html, encoding="utf-8")
    print(f"OGP HTML生成: {list_out_path}")


def sync_to_production(payload: dict) -> bool:
    """POST note data to production API. Returns True on success."""
    import requests

    api_url = os.environ.get("PRODUCTION_API_URL", "")
    api_key = os.environ.get("NOTES_API_KEY", "")

    if not api_url:
        print("Warning: PRODUCTION_API_URL が未設定のためスキップ")
        return False
    if not api_key:
        print("Warning: NOTES_API_KEY が未設定のためスキップ")
        return False

    try:
        resp = requests.post(
            api_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            print(f"Production sync OK (status={resp.status_code})")
            return True
        else:
            print(f"Production sync failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"Production sync error: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Publish a Markdown note to DB")
    parser.add_argument("markdown_file", help="Path to Markdown file with frontmatter")
    parser.add_argument(
        "--sync-production",
        action="store_true",
        help="Also sync to production API",
    )
    args = parser.parse_args()

    filepath = Path(args.markdown_file)
    if not filepath.is_absolute():
        # BASE_DIRを基準に解決（Docker: /app, 本番: プロジェクトルート）
        filepath = BASE_DIR / filepath

    if not filepath.exists():
        print(f"Error: ファイルが見つかりません: {filepath}")
        sys.exit(1)

    # Parse markdown
    text = filepath.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(text)

    slug = metadata.get("slug") or extract_slug(filepath)
    title = metadata.get("title", "")
    summary = metadata.get("summary", "")
    published_at = metadata.get("publishedAt", "")
    updated_at = metadata.get("updatedAt", "")

    if not title:
        print("Error: frontmatterにtitleが必要です")
        sys.exit(1)
    if not published_at:
        print("Error: frontmatterにpublishedAtが必要です")
        sys.exit(1)

    # Build payload
    payload = {
        "slug": slug,
        "title": title,
        "summary": summary,
        "content": body,
        "published_at": published_at,
        "status": "published",
    }
    if updated_at:
        payload["updated_at"] = updated_at

    # Local DB upsert
    from src.app import create_app  # noqa: E402

    app = create_app()
    with app.app_context():
        from src.services.note_service import NoteService  # noqa: E402

        service = NoteService()
        result = service.sync_note(payload.copy())
        print(f"DB upsert OK: slug={result['slug']}, id={result['id']}")

    # OGP HTML生成
    generate_ogp_html(slug, title, summary)

    # Production sync
    sync_ok = None
    if args.sync_production:
        sync_ok = sync_to_production(payload)

    # Summary
    print("\n--- Summary ---")
    print(f"  File:  {filepath}")
    print(f"  Slug:  {slug}")
    print(f"  Title: {title}")
    print(f"  DB:    OK")
    if args.sync_production:
        print(f"  Prod:  {'OK' if sync_ok else 'FAILED'}")


if __name__ == "__main__":
    main()
