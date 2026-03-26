"""Custom decorators for route protection."""
import hmac
import os
from functools import wraps

from flask import jsonify, request
from flask_login import current_user


def api_key_required(f):
    """
    Decorator that requires a valid API key in Authorization header.

    Validates against the NOTES_API_KEY environment variable.
    Header format: Authorization: Bearer <key>

    Usage:
        @bp.route("/sync")
        @api_key_required
        def sync_endpoint():
            ...
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = os.environ.get("NOTES_API_KEY")
        if not api_key:
            return jsonify(
                {
                    "success": False,
                    "error": {"message": "APIキーが設定されていません", "code": 403},
                }
            ), 403

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify(
                {
                    "success": False,
                    "error": {"message": "APIキーが必要です", "code": 403},
                }
            ), 403

        provided_key = auth_header[7:]  # Remove "Bearer " prefix
        if not hmac.compare_digest(provided_key, api_key):
            return jsonify(
                {
                    "success": False,
                    "error": {"message": "無効なAPIキーです", "code": 403},
                }
            ), 403

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorator that requires admin privileges.

    Must be used after @login_required to ensure user is authenticated.

    Usage:
        @bp.route("/admin-only")
        @login_required
        @admin_required
        def admin_only_route():
            ...
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify(
                {
                    "success": False,
                    "error": {"message": "管理者権限が必要です", "code": 403},
                }
            ), 403
        return f(*args, **kwargs)

    return decorated_function
