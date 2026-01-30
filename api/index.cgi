#!/home/kima3/.pyenv/versions/3.9.18/bin/python3
# -*- coding: utf-8 -*-
"""Flask CGI entry point for Sakura rental server."""

import os
import sys
from pathlib import Path

# プロジェクトルートを特定
APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT / "backend"))

# venv有効化（本番環境）
venv_site_packages = APP_ROOT / "backend" / "venv" / "lib" / "python3.9" / "site-packages"
if venv_site_packages.exists():
    sys.path.insert(0, str(venv_site_packages))

# .env読み込み
env_file = APP_ROOT / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# 環境変数設定（本番環境用）
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("APP_BASE_DIR", str(APP_ROOT))
os.environ.setdefault("APP_DATA_DIR", str(APP_ROOT / "data"))

# カレントディレクトリをプロジェクトルートに変更（相対パス解決用）
os.chdir(APP_ROOT)

# Flaskアプリケーション読み込み（エラー詳細捕捉）
print("Content-Type: text/plain\n", flush=True)
try:
    print(f"Importing Flask app...", flush=True)
    print(f"CWD: {os.getcwd()}", flush=True)
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}", flush=True)
    from src.app import app
    print(f"SUCCESS: Flask app loaded", flush=True)
except Exception as e:
    import traceback
    print(f"ERROR: {e}", flush=True)
    print(f"\nFull traceback:", flush=True)
    traceback.print_exc()
    import sys
    sys.exit(1)
from wsgiref.handlers import CGIHandler

# CGIハンドラーで実行
if __name__ == "__main__":
    CGIHandler().run(app)
