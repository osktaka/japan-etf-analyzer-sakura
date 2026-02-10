"""Market analysis API routes."""
from flask import Blueprint, request

from src.services import MarketService
from src.utils import api_response, error_response


def create_market_bp():
    """Create market analysis blueprint."""
    bp = Blueprint("market", __name__, url_prefix="/market")
    service = MarketService()

    @bp.route("/tag-momentum", methods=["GET"])
    def get_tag_momentum():
        """Get tag-momentum cross-tabulation data.

        GET /api/v1/market/tag-momentum

        Query Parameters:
            category: Optional tag category filter

        Returns:
            Tag-momentum analysis data
        """
        category = request.args.get("category")

        try:
            result = service.get_tag_momentum(category=category)
        except Exception:
            return error_response("Failed to retrieve tag momentum data", 500)

        return api_response(data=result)

    return bp
