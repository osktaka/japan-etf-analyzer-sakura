"""Application configuration settings."""
import os
from pathlib import Path


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # データディレクトリ（Docker内: /app/data）
    BASE_DIR = Path("/app")
    DATA_DIR = BASE_DIR / "data"

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
