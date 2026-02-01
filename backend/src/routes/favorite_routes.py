"""Favorite API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.services.favorite_service import FavoriteService
from src.utils import api_response, error_response


def create_favorite_bp():
    """Create favorite blueprint."""
    bp = Blueprint("favorites", __name__, url_prefix="/favorites")
    favorite_service = FavoriteService()

    @bp.route("", methods=["GET"])
    @login_required
    def get_favorites():
        """Get user's favorites.

        GET /api/v1/favorites

        Query Parameters:
            perspective: Perspective ID for score calculation (balance, dividend, etc.). Default: balance
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            List of user's favorite ETFs with scores
        """
        perspective = request.args.get("perspective", "balance")
        scoring_mode = request.args.get("scoring_mode", "full")

        if scoring_mode not in ("full", "partial"):
            scoring_mode = "full"

        favorites = favorite_service.get_user_favorites(
            current_user.id, perspective=perspective, scoring_mode=scoring_mode
        )
        return api_response(data=favorites)

    @bp.route("", methods=["POST"])
    @login_required
    def add_favorite():
        """Add ETF to favorites.

        POST /api/v1/favorites

        Request Body:
            {
                "etf_code": "1306"
            }

        Returns:
            Created favorite data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        etf_code = data.get("etf_code", "").strip()

        if not etf_code:
            return error_response("ETFコードは必須です", 400)

        favorite, error = favorite_service.add_favorite(current_user.id, etf_code)

        if error:
            return error_response(error, 400)

        return api_response(
            data=favorite.to_dict(),
            message="お気に入りに追加しました",
            status_code=201,
        )

    @bp.route("/<etf_code>", methods=["DELETE"])
    @login_required
    def remove_favorite(etf_code: str):
        """Remove ETF from favorites.

        DELETE /api/v1/favorites/{etf_code}

        Args:
            etf_code: ETF code to remove from favorites

        Returns:
            Success message
        """
        success, error = favorite_service.remove_favorite(current_user.id, etf_code)

        if error:
            return error_response(error, 400)

        return api_response(message="お気に入りから削除しました")

    @bp.route("/codes", methods=["GET"])
    @login_required
    def get_favorite_codes():
        """Get list of favorited ETF codes.

        GET /api/v1/favorites/codes

        Returns:
            List of ETF codes
        """
        codes = favorite_service.get_favorite_codes(current_user.id)
        return api_response(data=codes)

    @bp.route("/check/<etf_code>", methods=["GET"])
    @login_required
    def check_favorite(etf_code: str):
        """Check if ETF is favorited.

        GET /api/v1/favorites/check/{etf_code}

        Args:
            etf_code: ETF code to check

        Returns:
            is_favorited boolean
        """
        is_favorited = favorite_service.is_favorited(current_user.id, etf_code)
        return api_response(data={"is_favorited": is_favorited})

    return bp
