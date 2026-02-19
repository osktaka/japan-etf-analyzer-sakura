"""Demo API routes - read-only endpoints for unauthenticated users."""
from flask import Blueprint, request

from src.models import User
from src.services.cash_flow_service import CashFlowService
from src.services.favorite_service import FavoriteService
from src.services.portfolio_service import PortfolioService
from src.services.trade_service import TradeService
from src.utils import api_response

# Module-level cache for demo user PK
_demo_user_pk = None


def _get_demo_user_pk():
    """Get demo user's PK (integer), cached after first lookup."""
    global _demo_user_pk
    if _demo_user_pk is None:
        user = User.query.filter_by(user_id="demo").first()
        if user:
            _demo_user_pk = user.id
    return _demo_user_pk


def _empty_portfolio_summary():
    """Return empty portfolio summary structure."""
    return {
        "total_value": 0,
        "total_cost": 0,
        "total_unrealized_pnl": 0,
        "total_unrealized_pnl_percent": 0,
        "holdings_count": 0,
        "cash_balance": 0,
        "total_asset": 0,
    }


def create_demo_bp():
    """Create demo blueprint."""
    bp = Blueprint("demo", __name__, url_prefix="/demo")
    portfolio_service = PortfolioService()
    favorite_service = FavoriteService()
    trade_service = TradeService()
    cash_flow_service = CashFlowService()

    @bp.route("/portfolio", methods=["GET"])
    def get_portfolio_summary():
        """Get demo portfolio summary.

        GET /api/v1/demo/portfolio
        """
        user_pk = _get_demo_user_pk()
        if not user_pk:
            return api_response(data=_empty_portfolio_summary())
        summary = portfolio_service.get_portfolio_summary(user_pk)
        return api_response(data=summary)

    @bp.route("/portfolio/holdings", methods=["GET"])
    def get_holdings():
        """Get demo user's current holdings.

        GET /api/v1/demo/portfolio/holdings?include_sold=true

        Query params:
            include_sold: Include fully sold holdings ('true'/'false'). Default: 'false'
        """
        user_pk = _get_demo_user_pk()
        if not user_pk:
            return api_response(data=[])
        include_sold = request.args.get("include_sold", "false").lower() == "true"
        holdings = portfolio_service.get_holdings(user_pk, include_sold=include_sold)
        return api_response(data=holdings)

    @bp.route("/portfolio/valuation-history", methods=["GET"])
    def get_valuation_history():
        """Get demo portfolio valuation history.

        GET /api/v1/demo/portfolio/valuation-history?period=1y
        """
        user_pk = _get_demo_user_pk()
        if not user_pk:
            return api_response(data=[])
        period = request.args.get("period", "1y")
        if period not in ("1m", "3m", "6m", "1y", "3y", "5y", "10y", "20y"):
            period = "1y"
        history = portfolio_service.get_valuation_history(user_pk, period)
        return api_response(data=history)

    @bp.route("/favorites", methods=["GET"])
    def get_favorites():
        """Get demo user's favorites.

        GET /api/v1/demo/favorites
        """
        user_pk = _get_demo_user_pk()
        if not user_pk:
            return api_response(data=[])
        perspective = request.args.get("perspective", "balance")
        scoring_mode = request.args.get("scoring_mode", "full")
        if scoring_mode not in ("full", "partial"):
            scoring_mode = "full"
        favorites = favorite_service.get_user_favorites(
            user_pk, perspective=perspective, scoring_mode=scoring_mode
        )
        return api_response(data=favorites)

    @bp.route("/trades", methods=["GET"])
    def get_trades():
        """Get demo user's trades.

        GET /api/v1/demo/trades
        """
        user_pk = _get_demo_user_pk()
        if not user_pk:
            return api_response(data=[])
        trades = trade_service.get_user_trades(user_id=user_pk)
        return api_response(data=trades)

    @bp.route("/cash-flows", methods=["GET"])
    def get_cash_flows():
        """Get demo user's cash flows.

        GET /api/v1/demo/cash-flows
        """
        user_pk = _get_demo_user_pk()
        if not user_pk:
            return api_response(data=[])
        cash_flows = cash_flow_service.get_user_cash_flows(user_pk)
        return api_response(data=cash_flows)

    return bp
