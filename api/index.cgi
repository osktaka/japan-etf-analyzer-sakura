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

# DATABASE_URLを絶対パスに変更（CGI環境での相対パス問題を回避）
db_path = APP_ROOT / "data" / "etf.db"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

# カレントディレクトリをプロジェクトルートに変更（相対パス解決用）
os.chdir(APP_ROOT)

# Flaskアプリケーション読み込み
try:
    from src.app import app
except Exception as e:
    # エラー時のみデバッグ情報を出力
    print("Content-Type: text/plain\n", flush=True)
    print(f"ERROR: Failed to load Flask app", flush=True)
    print(f"CWD: {os.getcwd()}", flush=True)
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}", flush=True)
    print(f"\n{e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

from wsgiref.handlers import CGIHandler


# WSGI middleware to adjust PATH_INFO for CGI environment
class PrefixMiddleware:
    """Add prefix to PATH_INFO to match Flask route definitions."""

    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if "PATH_INFO" in environ:
            environ["PATH_INFO"] = self.prefix + environ["PATH_INFO"]
        # Apache CGI環境ではAuthorizationヘッダーが渡されないため
        # .htaccessのRewriteRuleで設定した環境変数から復元
        http_auth = environ.get("HTTP_AUTHORIZATION") or os.environ.get(
            "HTTP_AUTHORIZATION"
        )
        if http_auth and "HTTP_AUTHORIZATION" not in environ:
            environ["HTTP_AUTHORIZATION"] = http_auth
        return self.app(environ, start_response)


# Wrap app with middleware to add /api prefix
app = PrefixMiddleware(app, "/api")

# CGIハンドラーで実行
if __name__ == "__main__":
    CGIHandler().run(app)
