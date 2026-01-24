"""Database models package."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()


from .category import Category
from .tag import Tag
from .etf import ETF
from .etf_tag_relation import ETFTagRelation

__all__ = ["db", "init_db", "Category", "Tag", "ETF", "ETFTagRelation"]
