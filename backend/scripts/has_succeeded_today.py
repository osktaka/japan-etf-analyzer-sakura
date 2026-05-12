#!/usr/bin/env python3
"""指定バッチが今日（JST）成功しているかを判定する軽量ヘルパー.

cron-batch.sh の catch-up sweep から呼ばれる。

Exit codes:
    0: 当日成功記録あり（catch-up 不要）
    1: 当日成功記録なし（catch-up 対象）
    2: エラー（引数不正・DB接続失敗など）
"""
import os
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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: has_succeeded_today.py <batch_name>", file=sys.stderr)
        return 2

    batch_name = sys.argv[1].strip()
    if not batch_name:
        print("error: batch_name must not be empty", file=sys.stderr)
        return 2

    try:
        from src.app import create_app
        from src.repositories.batch_log_repository import BatchLogRepository

        app = create_app()
        with app.app_context():
            repo = BatchLogRepository()
            latest = repo.get_latest_success_time(batch_name)
            return 0 if latest is not None else 1
    except Exception as e:  # noqa: BLE001 - top-level safety net for shell caller
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
