"""Application configuration settings."""
import os
from pathlib import Path


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # セッションCookie（CSRF対策のSameSite、XSS経由の窃取対策のHttpOnly）
    # SECUREは本番のみTrue（devでTrueにするとHTTPでCookieが送信されずログイン不可になる）
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False

    # データディレクトリ（環境変数で上書き可能）
    BASE_DIR = Path(os.environ.get("APP_BASE_DIR", "/app"))
    DATA_DIR = Path(os.environ.get("APP_DATA_DIR", str(BASE_DIR / "data")))

    # モックデータ使用フラグ（True: モック、False: 本番yfinance）
    USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "true").lower() == "true"

    # キャッシュTTL（秒）
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))

    @classmethod
    def init_app(cls, app):
        """Initialize application with this config."""
        # テスト時は in-memory DB のため DATA_DIR 不要。CI（/app 非存在・APP_BASE_DIR未設定）
        # での mkdir 失敗を避けるためスキップする。
        if not app.config.get("TESTING"):
            cls.DATA_DIR.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{Config.DATA_DIR / 'etf.db'}"
    )
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{Config.DATA_DIR / 'etf.db'}"
    )
    SESSION_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        """Initialize production app, refusing to boot with an insecure SECRET_KEY."""
        super().init_app(app)
        secret_key = app.config.get("SECRET_KEY")
        if not secret_key or secret_key == "dev-secret-key":
            raise RuntimeError(
                "本番環境ではSECRET_KEYを必ず設定してください"
                "（環境変数 SECRET_KEY が未設定、または既定値のままです）"
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
