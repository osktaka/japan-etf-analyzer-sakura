"""Admin API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.models import User, db
from src.repositories.batch_log_repository import BatchLogRepository
from src.utils import api_response, error_response
from src.utils.decorators import admin_required


def create_admin_bp():
    """Create admin blueprint."""
    bp = Blueprint("admin", __name__, url_prefix="/admin")
    batch_log_repo = BatchLogRepository()

    @bp.route("/users", methods=["GET"])
    @login_required
    @admin_required
    def get_users():
        """Get all users.

        GET /api/v1/admin/users

        Returns:
            List of users with id, email, username, is_admin, last_login_at, created_at
        """
        users = db.session.query(User).order_by(User.created_at.desc()).all()
        return api_response(data=[user.to_dict() for user in users])

    @bp.route("/users/<int:user_id>", methods=["PATCH"])
    @login_required
    @admin_required
    def update_user(user_id: int):
        """Update user admin status.

        PATCH /api/v1/admin/users/<user_id>

        Request Body:
            {
                "is_admin": true/false
            }

        Returns:
            Updated user data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        if "is_admin" not in data:
            return error_response("is_admin フィールドが必要です", 400)

        # 自分自身の管理者権限は変更不可
        if user_id == current_user.id:
            return error_response("自分自身の管理者権限は変更できません", 400)

        user = db.session.get(User, user_id)
        if not user:
            return error_response("ユーザーが見つかりません", 404)

        user.is_admin = bool(data["is_admin"])
        db.session.commit()

        return api_response(
            data=user.to_dict(),
            message="ユーザー情報を更新しました",
        )

    @bp.route("/batch-logs", methods=["GET"])
    @login_required
    @admin_required
    def get_batch_logs():
        """Get batch execution logs.

        GET /api/v1/admin/batch-logs

        Query Parameters:
            limit: Maximum number of logs to return (default: 100)

        Returns:
            List of batch logs
        """
        limit = request.args.get("limit", 100, type=int)
        logs = batch_log_repo.get_all(limit=limit)
        return api_response(data=[log.to_dict() for log in logs])

    return bp
