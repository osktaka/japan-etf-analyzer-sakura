"""Application configuration settings."""
import os
from pathlib import Path


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

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
        cls.DATA_DIR.mkdir(exist_ok=True)


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


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
