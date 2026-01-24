"""Flask application entry point."""
import os

from flask import Flask, jsonify
from flask_cors import CORS

from .config.settings import config
from .models import db
from .routes import register_routes


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)

    # 設定読み込み
    app.config.from_object(config.get(config_name, config["default"]))

    # CORS設定
    CORS(app)

    # データベース初期化
    db.init_app(app)
    with app.app_context():
        db.create_all()

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
