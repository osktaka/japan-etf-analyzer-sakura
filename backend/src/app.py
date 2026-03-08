"""Flask application entry point."""
import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException

from .config.settings import config
from .models import User, db
from .routes import register_routes

logger = logging.getLogger(__name__)

# Flask-Login manager
login_manager = LoginManager()


@event.listens_for(Engine, "connect")
def set_sqlite_wal_mode(dbapi_conn, connection_record):
    """SQLite接続時にWALモードを有効化する."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


@login_manager.user_loader
def load_user(user_id: str):
    """Load user by ID for Flask-Login."""
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access."""
    return jsonify(
        {"success": False, "error": {"message": "認証が必要です", "code": 401}}
    ), 401


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)

    # 設定読み込み
    app.config.from_object(config.get(config_name, config["default"]))

    # CORS設定（credentialsを許可）
    CORS(app, supports_credentials=True)

    # データベース初期化
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Flask-Login初期化
    login_manager.init_app(app)

    # APIルート登録
    register_routes(app)

    # ヘルスチェック
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    # API v1 ルート
    @app.route("/api/v1/")
    def api_root():
        return jsonify({"message": "Japan ETF Analyzer API", "version": "1.0.0"})

    # グローバルエラーハンドラー
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle uncaught exceptions."""
        # HTTPException（400番台など）はそのまま返す
        if isinstance(e, HTTPException):
            return e
        logger.exception(f"Unhandled exception: {e}")
        response = jsonify(
            {
                "success": False,
                "error": {"message": "サーバーエラーが発生しました", "code": 500},
            }
        )
        response.status_code = 500
        return response

    @app.errorhandler(500)
    def handle_500(e):
        """Handle 500 errors."""
        logger.error(f"500 error: {e}")
        response = jsonify(
            {
                "success": False,
                "error": {"message": "サーバーエラーが発生しました", "code": 500},
            }
        )
        response.status_code = 500
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
