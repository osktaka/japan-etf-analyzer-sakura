"""Database models package."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()


# Models must be imported after db is defined to avoid circular imports
from .category import Category  # noqa: E402
from .tag import Tag  # noqa: E402
from .etf import ETF  # noqa: E402
from .etf_tag_relation import ETFTagRelation  # noqa: E402
from .user import User  # noqa: E402
from .favorite import Favorite  # noqa: E402
from .trade import Trade  # noqa: E402
from .price_history import PriceHistory  # noqa: E402
from .performance_cache import PerformanceCache  # noqa: E402
from .score_cache import ScoreCache  # noqa: E402
from .batch_log import BatchLog  # noqa: E402
from .stock_split import StockSplit  # noqa: E402
from .user_settings import UserSettings  # noqa: E402
from .etf_metrics_history import EtfMetricsHistory  # noqa: E402
from .cash_flow import CashFlow  # noqa: E402
from .note import Note  # noqa: E402

__all__ = [
    "db",
    "init_db",
    "Category",
    "Tag",
    "ETF",
    "ETFTagRelation",
    "User",
    "Favorite",
    "Trade",
    "PriceHistory",
    "PerformanceCache",
    "ScoreCache",
    "BatchLog",
    "StockSplit",
    "UserSettings",
    "EtfMetricsHistory",
    "CashFlow",
    "Note",
]
