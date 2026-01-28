"""Routes package - API endpoints."""
from flask import Blueprint


def register_routes(app):
    """Register all API routes with the Flask app."""
    from .admin_routes import create_admin_bp
    from .auth_routes import create_auth_bp
    from .category_routes import create_category_bp
    from .compare_routes import create_compare_bp
    from .etf_routes import create_etf_bp
    from .favorite_routes import create_favorite_bp
    from .portfolio_routes import create_portfolio_bp
    from .recommend_routes import create_recommend_bp
    from .tag_routes import create_tag_bp
    from .trade_routes import create_trade_bp

    api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

    api_v1.register_blueprint(create_admin_bp())
    api_v1.register_blueprint(create_auth_bp())
    api_v1.register_blueprint(create_category_bp())
    api_v1.register_blueprint(create_compare_bp())
    api_v1.register_blueprint(create_tag_bp())
    api_v1.register_blueprint(create_etf_bp())
    api_v1.register_blueprint(create_recommend_bp())
    api_v1.register_blueprint(create_favorite_bp())
    api_v1.register_blueprint(create_trade_bp())
    api_v1.register_blueprint(create_portfolio_bp())

    app.register_blueprint(api_v1)
