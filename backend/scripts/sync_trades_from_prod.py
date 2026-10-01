"""Mirror a user's trades and cash flows from production into the local DB.

本番を正として、ローカルの対象ユーザーの trades / cash_flows を置換する。
既定は dry-run（差分表示のみ）。``--execute`` でバックアップ後に適用する。
本番側は読み取りのみ（GET /api/v1/sync/user-data、NOTES_API_KEY 必須）。
``--restore-from`` は取得元を本番ではなく同期バックアップに替え、対象ユーザー分だけを戻す。
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

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

import requests  # noqa: E402

PROD_URL = "https://kima3.net/japan-etf-analyzer"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", default="test", help="user_id (default: test)")
    parser.add_argument("--url", default=PROD_URL, help="source base URL")
    parser.add_argument(
        "--restore-from",
        metavar="BACKUP",
        help="restore this user's rows from a sync backup file instead of prod",
    )
    parser.add_argument(
        "--execute", action="store_true", help="apply (default: dry-run)"
    )
    parser.add_argument(
        "--allow-empty", action="store_true", help="allow replacing with empty data"
    )
    return parser.parse_args()


def in_container() -> bool:
    return Path("/.dockerenv").exists()


def fetch_remote(url: str, user: str) -> dict:
    """GET the user's data from production. Raises RuntimeError on failure."""
    parsed = urlparse(url)
    # Bearer キーを平文で送らない（開発サーバー向けの localhost だけ http を許す）
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
        raise RuntimeError(f"refusing non-https url: {url}")
    api_key = os.environ.get("NOTES_API_KEY", "")
    if not api_key:
        # env_file はコンテナ作成時に読まれるため、.env 変更後は再作成が要る
        raise RuntimeError(
            "NOTES_API_KEY is empty (after editing .env: docker compose up -d backend)"
        )
    try:
        resp = requests.get(
            url.rstrip("/") + "/api/v1/sync/user-data",
            params={"user_id": user},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"connection error: {exc}") from exc
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        data = resp.json()["data"]
        data["trades"], data["cash_flows"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"unexpected response body: {exc!r}") from exc
    return data


def backup_db(app, protect: Optional[Path] = None) -> Path:
    """Snapshot the SQLite file (WAL included) before replacing data."""
    from src.services.user_data_sync_service import backup_sqlite

    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    src = Path(uri.replace("sqlite:///", "", 1))
    return backup_sqlite(src, src.parent / "backups", protect=protect)


def print_diff(local_summary: dict, source_summary: dict, classified: dict) -> None:
    print(f"{'':18}{'local':>16}{'source':>16}")
    for key, sv in source_summary.items():
        lv = local_summary.get(key)
        mark = "" if lv == sv else "  <- differs"
        print(f"{key:18}{lv!s:>16}{sv!s:>16}{mark}")
    for name, c in classified.items():
        if c["created_at_only"]:
            print(
                f"-- {name}: {c['created_at_only']} rows differ only in created_at"
                " (replaced with the source value)"
            )
        for label, key in (
            ("local only (will be DELETED)", "local_only"),
            ("source only (will be ADDED)", "remote_only"),
        ):
            if c[key]:
                print(f"-- {name} {label}: {len(c[key])}")
                for row in c[key]:
                    print("   ", row)


def is_synced(diff: dict) -> bool:
    return not any(diff.values())


def main() -> int:
    args = parse_args()
    # 本番シェルで誤って実行すると自分自身を置換対象にしてしまう。.env を読まない
    # スクリプトでは環境変数のガードが働かないため、手順上の実行場所である
    # Docker コンテナ内であることを肯定的に確認する。
    # src.app は import 時に create_app() で DB を開くため、ガードの後に import する
    if not in_container():
        print("refusing to run outside the local Docker container")
        return 2

    from src.app import create_app
    from src.models import User
    from src.services.user_data_sync_service import (
        SyncError,
        classify_diff,
        diff_rows,
        export_user_data,
        read_user_data_from_sqlite,
        replace_user_data,
        summarize,
        validate_payload,
    )

    try:
        if args.restore_from:
            source = read_user_data_from_sqlite(Path(args.restore_from), args.user)
        else:
            source = fetch_remote(args.url, args.user)
    except (RuntimeError, SyncError, OSError, sqlite3.Error) as exc:
        print(f"source failed: {exc}")
        return 1

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(user_id=args.user).first()
        if not user:
            print(f"local user not found: {args.user}")
            return 1
        local = export_user_data(user.id)
        diff = diff_rows(local, source)
        print_diff(
            local["summary"],
            summarize(source["trades"], source["cash_flows"]),
            classify_diff(diff),
        )

        if is_synced(diff):
            print("already in sync")
            return 0
        # バックアップ（約200MB）を取る前に、適用できないペイロードを弾く
        try:
            validate_payload(source, allow_empty=args.allow_empty)
        except SyncError as exc:
            print(f"aborted: {exc}")
            return 1
        if not args.execute:
            print("dry-run: no changes (use --execute to apply)")
            return 0

        restore_src = Path(args.restore_from) if args.restore_from else None
        print(f"backup: {backup_db(app, protect=restore_src)}")
        try:
            replace_user_data(user.id, source, allow_empty=args.allow_empty)
        except Exception as exc:  # DB ロック等。置換はロールバック済み
            print(f"aborted (rolled back): {exc!r}")
            return 1
        after = export_user_data(user.id)
        if not is_synced(diff_rows(after, source)):
            print("VERIFY FAILED: local rows differ from the source after replace")
            return 1
        print("synced and verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
