"""Migrate existing markdown notes to the database."""
import os
import re
import sys
from datetime import datetime
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

from src.app import create_app  # noqa: E402
from src.repositories.note_repository import NoteRepository  # noqa: E402

# NOTES_DIR: 環境変数で上書き可能、デフォルトはPROJECT_ROOT基準
NOTES_DIR = Path(
    os.environ.get(
        "NOTES_DIR",
        str(PROJECT_ROOT / "frontend" / "src" / "content" / "notes"),
    )
)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from markdown text.

    Returns (metadata_dict, body_content).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        raise ValueError("Frontmatter not found")

    meta_str = match.group(1)
    body = match.group(2).strip()

    metadata = {}
    for line in meta_str.split("\n"):
        line = line.strip()
        if not line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        metadata[key] = value

    return metadata, body


def parse_datetime(value: str) -> datetime:
    """Parse date or datetime string."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {value}")


def main():
    """Migrate markdown notes to database."""
    md_files = sorted(NOTES_DIR.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {NOTES_DIR}")
        return

    print(f"Found {len(md_files)} markdown files")
    print("=" * 60)

    app = create_app()
    repo = NoteRepository()

    success_count = 0
    error_count = 0
    errors = []

    with app.app_context():
        for md_file in md_files:
            slug = md_file.stem
            try:
                text = md_file.read_text(encoding="utf-8")
                metadata, body = parse_frontmatter(text)

                title = metadata.get("title", "")
                summary = metadata.get("summary", "")
                published_at_str = metadata.get("publishedAt", "")
                updated_at_str = metadata.get("updatedAt", "")

                if not title:
                    raise ValueError("title is missing")
                if not published_at_str:
                    raise ValueError("publishedAt is missing")

                published_at = parse_datetime(published_at_str)
                updated_at = (
                    parse_datetime(updated_at_str) if updated_at_str else None
                )

                data = {
                    "title": title,
                    "summary": summary,
                    "content": body,
                    "status": "published",
                    "published_at": published_at,
                }
                if updated_at:
                    data["updated_at"] = updated_at

                note = repo.upsert_by_slug(slug, data)
                action = "UPDATED" if note.id else "INSERTED"
                print(f"  OK: {slug} ({action})")
                success_count += 1

            except Exception as e:
                print(f"  ERROR: {slug} - {e}")
                error_count += 1
                errors.append((slug, str(e)))

    print("=" * 60)
    print(f"Total: {len(md_files)} files")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    if errors:
        print("\nError details:")
        for slug, msg in errors:
            print(f"  - {slug}: {msg}")


if __name__ == "__main__":
    main()
