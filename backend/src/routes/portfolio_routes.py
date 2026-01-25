"""Portfolio API routes."""
from flask import Blueprint
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

    return bp
