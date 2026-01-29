"""Portfolio API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.services.portfolio_service import PortfolioService
from src.utils import api_response


def create_portfolio_bp():
    """Create portfolio blueprint."""
    bp = Blueprint("portfolio", __name__, url_prefix="/portfolio")
    portfolio_service = PortfolioService()

    @bp.route("", methods=["GET"])
    @login_required
    def get_portfolio_summary():
        """Get portfolio summary.

        GET /api/v1/portfolio

        Returns:
            Portfolio summary with totals
        """
        summary = portfolio_service.get_portfolio_summary(current_user.id)
        return api_response(data=summary)

    @bp.route("/holdings", methods=["GET"])
    @login_required
    def get_holdings():
        """Get user's current holdings.

        GET /api/v1/portfolio/holdings

        Returns:
            List of holdings with P&L data
        """
        holdings = portfolio_service.get_holdings(current_user.id)
        return api_response(data=holdings)

    @bp.route("/valuation-history", methods=["GET"])
    @login_required
    def get_valuation_history():
        """Get portfolio valuation history.

        GET /api/v1/portfolio/valuation-history?period=1m

        Query params:
            period: Time period ('1m', '3m', '6m', '1y', '3y', '5y', '10y', '20y'). Default: '1y'

        Returns:
            List of {date, value} representing daily portfolio value
        """
        period = request.args.get("period", "1y")
        if period not in ("1m", "3m", "6m", "1y", "3y", "5y", "10y", "20y"):
            period = "1y"

        history = portfolio_service.get_valuation_history(current_user.id, period)
        return api_response(data=history)

    return bp
