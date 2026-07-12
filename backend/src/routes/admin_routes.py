"""Admin API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.models import StockSplit, db
from src.repositories.batch_log_repository import BatchLogRepository
from src.repositories.stock_split_repository import StockSplitRepository
from src.repositories.user_repository import UserRepository
from src.utils import api_response, error_response
from src.utils.decorators import admin_required


def create_admin_bp():
    """Create admin blueprint."""
    bp = Blueprint("admin", __name__, url_prefix="/admin")
    batch_log_repo = BatchLogRepository()
    stock_split_repo = StockSplitRepository()
    user_repo = UserRepository()

    @bp.route("/users", methods=["GET"])
    @login_required
    @admin_required
    def get_users():
        """Get all users.

        GET /api/v1/admin/users

        Returns:
            List of users with id, user_id, username, is_admin, last_login_at, created_at
        """
        users = user_repo.get_all_ordered_by_created_desc()
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

        user = user_repo.update_admin_status(user_id, bool(data["is_admin"]))
        if not user:
            return error_response("ユーザーが見つかりません", 404)

        return api_response(
            data=user.to_dict(),
            message="ユーザー情報を更新しました",
        )

    @bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
    @login_required
    @admin_required
    def reset_user_password(user_id: int):
        """Reset user password to a newly generated temporary password.

        POST /api/v1/admin/users/<user_id>/reset-password

        Returns:
            Success message and the generated temporary password
            (data.temporary_password) for the admin to hand to the user
        """
        # 自分自身のパスワードはリセット不可
        if user_id == current_user.id:
            return error_response("自分自身のパスワードはリセットできません", 400)

        temporary_password = user_repo.reset_password(user_id)
        if temporary_password is None:
            return error_response("ユーザーが見つかりません", 404)

        return api_response(
            data={"temporary_password": temporary_password},
            message="パスワードをリセットしました",
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

    @bp.route("/batch-logs/<int:log_id>/reset", methods=["POST"])
    @login_required
    @admin_required
    def reset_batch_log(log_id: int):
        """Force a running batch job to failed status.

        POST /api/v1/admin/batch-logs/<log_id>/reset

        Returns:
            Updated batch log data
        """
        from datetime import datetime

        log = batch_log_repo.get_by_id(log_id)
        if not log:
            return error_response("バッチログが見つかりません", 404)

        if log.status != "running":
            return error_response(
                f"実行中のバッチのみリセット可能です（現在のステータス: {log.status}）",
                400,
            )

        updated_log = batch_log_repo.update(
            log_id,
            status="failed",
            finished_at=datetime.utcnow(),
            error_message="Manually reset by admin",
        )

        return api_response(
            data=updated_log.to_dict(),
            message="バッチを強制終了しました",
        )

    @bp.route("/stock-splits", methods=["GET"])
    @login_required
    @admin_required
    def get_stock_splits():
        """Get stock split candidates.

        GET /api/v1/admin/stock-splits

        Returns:
            List of stock splits with ETF names and needs_recalculation flag
        """
        from src.models import ETF, PerformanceCache

        # Get all splits with ETF names via LEFT JOIN
        splits_with_names = (
            db.session.query(StockSplit, ETF.name)
            .outerjoin(ETF, StockSplit.etf_code == ETF.code)
            .all()
        )

        result = []
        for split, etf_name in splits_with_names:
            split_dict = split.to_dict()
            split_dict["etf_name"] = etf_name

            # Calculate needs_recalculation flag
            # Needed if chart is applied AND (no cache exists OR cache is older than review)
            needs_recalculation = False
            if split.is_chart_applied:
                # Check if any performance cache exists for this ETF
                cache_exists = (
                    db.session.query(PerformanceCache)
                    .filter(PerformanceCache.etf_code == split.etf_code)
                    .first()
                )

                if not cache_exists:
                    # No cache at all
                    needs_recalculation = True
                elif split.reviewed_at and cache_exists.calculated_at:
                    # Cache exists but is older than review
                    needs_recalculation = cache_exists.calculated_at < split.reviewed_at

            split_dict["needs_recalculation"] = needs_recalculation
            result.append(split_dict)

        return api_response(data=result)

    @bp.route("/stock-splits/<int:split_id>", methods=["PATCH"])
    @login_required
    @admin_required
    def update_stock_split(split_id: int):
        """Update stock split applied status.

        PATCH /api/v1/admin/stock-splits/<split_id>

        Request Body:
            {
                "is_applied": true or false (optional),
                "is_chart_applied": true or false (optional)
            }

        Returns:
            Updated stock split data with ETF name
        """
        from datetime import datetime

        from src.models import ETF

        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        if "is_applied" not in data and "is_chart_applied" not in data:
            return error_response(
                "is_applied または is_chart_applied フィールドが必要です", 400
            )

        split = stock_split_repo.get_by_id(split_id)
        if not split:
            return error_response("株式分割が見つかりません", 404)

        # Update fields if provided
        if "is_applied" in data:
            split.is_applied = bool(data["is_applied"])
        if "is_chart_applied" in data:
            split.is_chart_applied = bool(data["is_chart_applied"])

        split.reviewed_at = datetime.utcnow()
        split.reviewed_by = current_user.id
        db.session.commit()

        # Get ETF name via JOIN
        etf_name = (
            db.session.query(ETF.name).filter(ETF.code == split.etf_code).scalar()
        )

        split_dict = split.to_dict()
        split_dict["etf_name"] = etf_name

        return api_response(
            data=split_dict,
            message="株式分割の設定を更新しました",
        )

    @bp.route("/stock-splits/<int:split_id>/recalculate", methods=["POST"])
    @login_required
    @admin_required
    def recalculate_performance_cache(split_id: int):
        """Recalculate performance cache for an ETF with split adjustments.

        POST /api/v1/admin/stock-splits/<split_id>/recalculate

        Returns:
            Result with etf_code and updated_periods
        """
        from src.services.performance_cache_service import PerformanceCacheService

        split = stock_split_repo.get_by_id(split_id)
        if not split:
            return error_response("株式分割が見つかりません", 404)

        try:
            service = PerformanceCacheService()
            result = service.recalculate_for_split(split_id)

            if not result:
                return error_response(
                    "パフォーマンスキャッシュの再計算に失敗しました", 500
                )

            return api_response(
                data=result,
                message=f"ETF {result['etf_code']} のパフォーマンスキャッシュを再計算しました",
            )

        except Exception as e:
            return error_response(f"再計算中にエラーが発生しました: {str(e)}", 500)

    return bp
