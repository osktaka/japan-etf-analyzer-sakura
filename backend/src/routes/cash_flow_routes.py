"""CashFlow API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.services.cash_flow_service import CashFlowService
from src.utils import api_response, error_response


def create_cash_flow_bp():
    """Create cash flow blueprint."""
    bp = Blueprint("cash_flows", __name__, url_prefix="/cash-flows")
    cash_flow_service = CashFlowService()

    @bp.route("", methods=["GET"])
    @login_required
    def get_cash_flows():
        """Get user's cash flows.

        GET /api/v1/cash-flows
        GET /api/v1/cash-flows?start_date=2025-01-01&end_date=2025-12-31

        Query Parameters:
            start_date: Filter on or after this date (YYYY-MM-DD)
            end_date: Filter on or before this date (YYYY-MM-DD)

        Returns:
            List of user's cash flow records
        """
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        cash_flows = cash_flow_service.get_cash_flows_by_date_range(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )

        return api_response(data=cash_flows)

    @bp.route("", methods=["POST"])
    @login_required
    def create_cash_flow():
        """Create a new cash flow.

        POST /api/v1/cash-flows

        Request Body:
            {
                "flow_type": "deposit",
                "amount": 100000,
                "flow_date": "2025-01-15",
                "memo": "optional memo"
            }

        Returns:
            Created cash flow data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        required_fields = ["flow_type", "amount", "flow_date"]
        for field in required_fields:
            if field not in data:
                return error_response(f"{field}は必須です", 400)

        cash_flow, error = cash_flow_service.create_cash_flow(
            user_id=current_user.id,
            flow_type=data["flow_type"],
            amount=data["amount"],
            flow_date=data["flow_date"],
            memo=data.get("memo"),
        )

        if error:
            return error_response(error, 400)

        return api_response(
            data=cash_flow.to_dict(),
            message="入出金を登録しました",
            status_code=201,
        )

    @bp.route("/<int:cash_flow_id>", methods=["PUT"])
    @login_required
    def update_cash_flow(cash_flow_id: int):
        """Update a cash flow.

        PUT /api/v1/cash-flows/{cash_flow_id}

        Request Body (all fields optional):
            {
                "flow_type": "withdrawal",
                "amount": 50000,
                "flow_date": "2025-01-20",
                "memo": "updated memo"
            }

        Returns:
            Updated cash flow data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        cash_flow, error = cash_flow_service.update_cash_flow(
            user_id=current_user.id,
            cash_flow_id=cash_flow_id,
            flow_type=data.get("flow_type"),
            amount=data.get("amount"),
            flow_date=data.get("flow_date"),
            memo=data.get("memo"),
        )

        if error:
            return error_response(error, 400)

        return api_response(
            data=cash_flow.to_dict(),
            message="入出金を更新しました",
        )

    @bp.route("/<int:cash_flow_id>", methods=["DELETE"])
    @login_required
    def delete_cash_flow(cash_flow_id: int):
        """Delete a cash flow.

        DELETE /api/v1/cash-flows/{cash_flow_id}

        Returns:
            Success message
        """
        success, error = cash_flow_service.delete_cash_flow(
            current_user.id, cash_flow_id
        )

        if error:
            return error_response(error, 400)

        return api_response(message="入出金を削除しました")

    return bp
