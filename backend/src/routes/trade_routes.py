"""Trade API routes."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from src.services.trade_service import TradeService
from src.utils import api_response, error_response


def create_trade_bp():
    """Create trade blueprint."""
    bp = Blueprint("trades", __name__, url_prefix="/trades")
    trade_service = TradeService()

    @bp.route("", methods=["GET"])
    @login_required
    def get_trades():
        """Get user's trades.

        GET /api/v1/trades
        GET /api/v1/trades?etf_code=1306
        GET /api/v1/trades?start_date=2025-01-01&end_date=2025-12-31
        GET /api/v1/trades?search=TOPIX

        Query Parameters:
            etf_code: Filter by specific ETF code
            start_date: Filter trades on or after this date (YYYY-MM-DD)
            end_date: Filter trades on or before this date (YYYY-MM-DD)
            search: Search ETF code or name (partial match)

        Returns:
            List of user's trade records
        """
        etf_code = request.args.get("etf_code")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        search = request.args.get("search")

        if etf_code:
            # etf_codeが指定された場合は従来の動作（完全一致）
            trades = trade_service.get_trades_by_etf(current_user.id, etf_code)
        else:
            # フィルター検索（パラメータがなければ全件取得）
            trades = trade_service.get_user_trades(
                user_id=current_user.id,
                start_date=start_date,
                end_date=end_date,
                search=search,
            )

        return api_response(data=trades)

    @bp.route("", methods=["POST"])
    @login_required
    def create_trade():
        """Create a new trade.

        POST /api/v1/trades

        Request Body:
            {
                "etf_code": "1306",
                "trade_type": "buy",
                "quantity": 10,
                "price": 2345.00,
                "trade_date": "2025-01-15",
                "memo": "optional memo"
            }

        Returns:
            Created trade data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        required_fields = ["etf_code", "trade_type", "quantity", "price", "trade_date"]
        for field in required_fields:
            if field not in data:
                return error_response(f"{field}は必須です", 400)

        trade, error = trade_service.create_trade(
            user_id=current_user.id,
            etf_code=data["etf_code"],
            trade_type=data["trade_type"],
            quantity=data["quantity"],
            price=data["price"],
            trade_date=data["trade_date"],
            memo=data.get("memo"),
        )

        if error:
            return error_response(error, 400)

        return api_response(
            data=trade.to_dict(),
            message="取引を登録しました",
            status_code=201,
        )

    @bp.route("/<int:trade_id>", methods=["GET"])
    @login_required
    def get_trade(trade_id: int):
        """Get a single trade by ID.

        GET /api/v1/trades/{trade_id}

        Returns:
            Trade data
        """
        trade_data, error = trade_service.get_trade_by_id(current_user.id, trade_id)

        if error:
            return error_response(error, 404)

        return api_response(data=trade_data)

    @bp.route("/<int:trade_id>", methods=["PUT"])
    @login_required
    def update_trade(trade_id: int):
        """Update a trade.

        PUT /api/v1/trades/{trade_id}

        Request Body (all fields optional):
            {
                "trade_type": "sell",
                "quantity": 5,
                "price": 2400.00,
                "trade_date": "2025-01-20",
                "memo": "updated memo"
            }

        Returns:
            Updated trade data
        """
        data = request.get_json()

        if not data:
            return error_response("リクエストボディが必要です", 400)

        trade, error = trade_service.update_trade(
            user_id=current_user.id,
            trade_id=trade_id,
            trade_type=data.get("trade_type"),
            quantity=data.get("quantity"),
            price=data.get("price"),
            trade_date=data.get("trade_date"),
            memo=data.get("memo"),
        )

        if error:
            return error_response(error, 400)

        return api_response(
            data=trade.to_dict(),
            message="取引を更新しました",
        )

    @bp.route("/<int:trade_id>", methods=["DELETE"])
    @login_required
    def delete_trade(trade_id: int):
        """Delete a trade.

        DELETE /api/v1/trades/{trade_id}

        Returns:
            Success message
        """
        success, error = trade_service.delete_trade(current_user.id, trade_id)

        if error:
            return error_response(error, 400)

        return api_response(message="取引を削除しました")

    return bp
