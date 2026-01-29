"""Admin API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.models import User, db
from src.repositories.batch_log_repository import BatchLogRepository
from src.repositories.stock_split_repository import StockSplitRepository
from src.utils import api_response, error_response
from src.utils.decorators import admin_required


def create_admin_bp():
    """Create admin blueprint."""
    bp = Blueprint("admin", __name__, url_prefix="/admin")
    batch_log_repo = BatchLogRepository()
    stock_split_repo = StockSplitRepository()

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

    @bp.route("/stock-splits", methods=["GET"])
    @login_required
    @admin_required
    def get_stock_splits():
        """Get stock split candidates.

        GET /api/v1/admin/stock-splits

        Query Parameters:
            status: Filter by status (pending, approved, rejected). Default: all

        Returns:
            List of stock splits
        """
        status = request.args.get("status", None)
        if status:
            splits = stock_split_repo.get_by_status(status)
        else:
            splits = stock_split_repo.get_all()
        return api_response(data=[split.to_dict() for split in splits])

    @bp.route("/stock-splits/<int:split_id>", methods=["PATCH"])
    @login_required
    @admin_required
    def update_stock_split(split_id: int):
        """Update stock split status (approve/reject).

        PATCH /api/v1/admin/stock-splits/<split_id>

        Request Body:
            {
                "status": "approved" or "rejected"
            }

        Returns:
            Updated stock split data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        if "status" not in data:
            return error_response("status フィールドが必要です", 400)

        status = data["status"]
        if status not in ["approved", "rejected"]:
            return error_response(
                "status は 'approved' または 'rejected' である必要があります", 400
            )

        split = stock_split_repo.update_status(split_id, status, current_user.id)
        if not split:
            return error_response("株式分割が見つかりません", 404)

        return api_response(
            data=split.to_dict(),
            message=f"株式分割を{('承認' if status == 'approved' else '却下')}しました",
        )

    return bp
