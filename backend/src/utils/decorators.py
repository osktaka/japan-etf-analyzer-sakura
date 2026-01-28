"""Custom decorators for route protection."""
from functools import wraps

from flask import jsonify
from flask_login import current_user


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
