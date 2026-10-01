"""Sync API routes - server-to-server export of a user's trades / cash flows."""
import os

from flask import Blueprint, request

from src.models import User
from src.services.user_data_sync_service import export_user_data
from src.utils import api_response, error_response
from src.utils.decorators import api_key_required


def _allowed_user_ids():
    """Users whose data may be exported (env SYNC_EXPORT_USER_IDS, default: test).

    NOTES_API_KEY は notes / demo 書込用の鍵で、他サービスの環境にも入っている。
    読み取り権限が全ユーザーに広がらないよう、対象を許可リストで絞る。
    """
    raw = os.environ.get("SYNC_EXPORT_USER_IDS", "test")
    return {u.strip() for u in raw.split(",") if u.strip()}


def create_sync_bp():
    """Create sync blueprint."""
    bp = Blueprint("sync", __name__, url_prefix="/sync")

    @bp.route("/user-data", methods=["GET"])
    @api_key_required
    def get_user_data():
        """Export a user's trades and cash flows.

        GET /api/v1/sync/user-data?user_id=test

        sync_trades_from_prod.py（ローカルが本番から取得する）専用。
        NOTES_API_KEY を Authorization: Bearer ヘッダで要求し、対象は
        SYNC_EXPORT_USER_IDS の許可リスト内のユーザーに限る。
        """
        user_id = request.args.get("user_id")
        if not user_id:
            return error_response("user_idは必須です", 400)
        if user_id not in _allowed_user_ids():
            return error_response("このユーザーは同期対象外です", 403)
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            return error_response("ユーザーが見つかりません", 404)
        return api_response(data=export_user_data(user.id))

    return bp
