"""Recommendation API routes."""
from flask import Blueprint, request

from src.services import RecommendService
from src.utils import api_response


def create_recommend_bp():
    """Create recommendation blueprint."""
    bp = Blueprint("recommendations", __name__)

    @bp.route("/perspectives", methods=["GET"])
    def get_perspectives():
        """Get available recommendation perspectives.

        GET /api/v1/perspectives

        Returns:
            List of available perspectives
        """
        service = RecommendService()
        perspectives = service.get_perspectives()

        return api_response(data=perspectives)

    @bp.route("/recommendations", methods=["GET"])
    def get_recommendations():
        """Get recommended ETFs based on perspective.

        GET /api/v1/recommendations

        Query Parameters:
            perspective: Perspective ID (dividend, low-cost, stability,
                         volume, growth, balance). Default: balance
            limit: Number of recommendations (default: 5, max: 20)

        Returns:
            Recommended ETFs with perspective info
        """
        perspective = request.args.get("perspective", "balance")
        limit = request.args.get("limit", 5, type=int)

        if limit < 1:
            limit = 5
        if limit > 20:
            limit = 20

        service = RecommendService()
        result = service.get_recommendations(perspective=perspective, limit=limit)

        return api_response(data=result)

    return bp
