"""User settings API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.services.user_settings_service import UserSettingsService
from src.utils import api_response, error_response


def create_user_settings_bp():
    """Create user settings blueprint."""
    bp = Blueprint("user_settings", __name__, url_prefix="/user")
    user_settings_service = UserSettingsService()

    @bp.route("/settings", methods=["GET"])
    @login_required
    def get_settings():
        """Get user settings (custom weights).

        GET /api/v1/user/settings

        Returns:
            User's custom weights in 0-1 format, or None if not set
        """
        custom_weights = user_settings_service.get_custom_weights(current_user.id)

        return api_response(
            data={
                "custom_weights": custom_weights
            }
        )

    @bp.route("/settings/custom-weights", methods=["PUT"])
    @login_required
    def update_custom_weights():
        """Update user's custom weights.

        PUT /api/v1/user/settings/custom-weights

        Request Body:
            {
                "weights": {
                    "dividend_power": 20,
                    "cost_efficiency": 20,
                    "scale_reliability": 20,
                    "trading_quality": 20,
                    "return_performance": 20
                }
            }

        Returns:
            Updated settings on success, error on validation failure
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        weights = data.get("weights")

        if not weights:
            return error_response("weightsフィールドは必須です", 400)

        try:
            settings = user_settings_service.save_custom_weights(
                current_user.id, weights
            )
            return api_response(
                data=settings.to_dict(),
                message="カスタム重みを更新しました"
            )
        except ValueError as e:
            return error_response(str(e), 400)

    return bp
