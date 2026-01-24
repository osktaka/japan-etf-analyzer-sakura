"""Flask application entry point."""
import os

from flask import Flask, jsonify
from flask_cors import CORS


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # CORS設定
    CORS(app)

    # 設定
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # ヘルスチェック
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    # API v1 ルート
    @app.route("/api/v1/")
    def api_root():
        return jsonify({
            "message": "Japan ETF Analyzer API",
            "version": "1.0.0"
        })

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
