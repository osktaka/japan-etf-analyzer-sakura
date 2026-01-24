"""Flask application entry point."""
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager

from .config.settings import config
from .models import User, db
from .routes import register_routes

# Flask-Login manager
login_manager = LoginManager()


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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
