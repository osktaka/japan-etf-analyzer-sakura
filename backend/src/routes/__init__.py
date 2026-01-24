"""Routes package - API endpoints."""
from flask import Blueprint


def register_routes(app):
    """Register all API routes with the Flask app."""
    from .category_routes import create_category_bp
    from .tag_routes import create_tag_bp
    from .etf_routes import create_etf_bp
    from .recommend_routes import create_recommend_bp

    api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

    api_v1.register_blueprint(create_category_bp())
    api_v1.register_blueprint(create_tag_bp())
    api_v1.register_blueprint(create_etf_bp())
    api_v1.register_blueprint(create_recommend_bp())

    app.register_blueprint(api_v1)
