"""Authentication API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.services.auth_service import AuthService
from src.utils import api_response, error_response


def create_auth_bp():
    """Create authentication blueprint."""
    bp = Blueprint("auth", __name__, url_prefix="/auth")
    auth_service = AuthService()

    @bp.route("/register", methods=["POST"])
    def register():
        """Register a new user.

        POST /api/v1/auth/register

        Request Body:
            {
                "user_id": "user123",
                "password": "password123",
                "username": "User Name"
            }

        Returns:
            User data on success, error on failure
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        user_id = data.get("user_id", "").strip()
        password = data.get("password", "")
        username = data.get("username", "").strip()

        user, error = auth_service.register(user_id, password, username)

        if error:
            return error_response(error, 400)

        return api_response(
            data=user.to_dict(),
            message="ユーザー登録が完了しました",
            status_code=201,
        )

    @bp.route("/login", methods=["POST"])
    def login():
        """Authenticate user and create session.

        POST /api/v1/auth/login

        Request Body:
            {
                "user_id": "user123",
                "password": "password123",
                "remember": false  // optional
            }

        Returns:
            User data on success, error on failure
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        user_id = data.get("user_id", "").strip()
        password = data.get("password", "")
        remember = data.get("remember", False)

        user, error = auth_service.login(user_id, password, remember)

        if error:
            return error_response(error, 401)

        return api_response(
            data=user.to_dict(),
            message="ログインしました",
        )

    @bp.route("/logout", methods=["POST"])
    @login_required
    def logout():
        """Logout current user.

        POST /api/v1/auth/logout

        Returns:
            Success message
        """
        auth_service.logout()
        return api_response(message="ログアウトしました")

    @bp.route("/me", methods=["GET"])
    @login_required
    def get_current_user():
        """Get current authenticated user.

        GET /api/v1/auth/me

        Returns:
            Current user data
        """
        return api_response(data=current_user.to_dict())

    return bp
