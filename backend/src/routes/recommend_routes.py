"""Recommendation API routes."""
from flask import Blueprint, request
from flask_login import current_user

from src.services import RecommendService
from src.utils import api_response, error_response


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
                         volume, growth, balance, custom). Default: balance
            limit: Number of recommendations (default: 5, max: 20)
            scoring_mode: Scoring mode - "full" (default, all 5 axes) or "partial" (data-available axes only)

        Returns:
            Recommended ETFs with perspective info
        """
        perspective = request.args.get("perspective", "balance")
        limit = request.args.get("limit", 5, type=int)
        scoring_mode = request.args.get("scoring_mode", "full")

        if limit < 1:
            limit = 5
        if limit > 20:
            limit = 20

        if scoring_mode not in ["full", "partial"]:
            scoring_mode = "full"

        # Get user_id if authenticated (required for custom perspective)
        user_id = current_user.id if current_user.is_authenticated else None

        service = RecommendService()
        try:
            result = service.get_recommendations(
                perspective=perspective,
                limit=limit,
                scoring_mode=scoring_mode,
                user_id=user_id
            )
            return api_response(data=result)
        except ValueError as e:
            return error_response(str(e), 400)

    return bp
