"""ETF API routes."""
from flask import Blueprint, request

from src.services import ChartService, ETFService
from src.utils import (
    api_response,
    error_response,
    validate_etf_code,
    validate_pagination,
)


def create_etf_bp():
    """Create ETF blueprint."""
    bp = Blueprint("etfs", __name__, url_prefix="/etfs")

    @bp.route("", methods=["GET"])
    def get_etfs():
        """Get ETFs with optional search/filter.

        GET /api/v1/etfs

        Query Parameters:
            keyword: Search keyword (name, code, description)
            category_id: Filter by category ID
            tag_ids: Filter by tag IDs (comma-separated)
            min_dividend_yield: Minimum dividend yield (%)
            max_expense_ratio: Maximum expense ratio (%)
            sort: Sort column (code, name, dividend_yield, expense_ratio, total_assets)
            order: Sort order (asc, desc). Default: asc
            limit: Number of results (default: 50, max: 100)
            offset: Pagination offset (default: 0)

        Returns:
            Paginated list of ETFs
        """
        keyword = request.args.get("keyword")
        category_id = request.args.get("category_id", type=int)
        tag_ids_param = request.args.get("tag_ids")
        min_dividend_yield = request.args.get("min_dividend_yield", type=float)
        max_expense_ratio = request.args.get("max_expense_ratio", type=float)
        sort = request.args.get("sort")
        order = request.args.get("order", "asc")

        if order not in ("asc", "desc"):
            return error_response("Invalid order parameter. Use 'asc' or 'desc'", 400)

        limit, offset, error = validate_pagination(
            request.args.get("limit"),
            request.args.get("offset"),
        )
        if error:
            return error_response(error, 400)

        tag_ids = None
        if tag_ids_param:
            try:
                tag_ids = [int(tid) for tid in tag_ids_param.split(",")]
            except ValueError:
                return error_response("Invalid tag_ids format", 400)

        service = ETFService()
        result = service.search(
            keyword=keyword,
            category_id=category_id,
            tag_ids=tag_ids,
            min_dividend_yield=min_dividend_yield,
            max_expense_ratio=max_expense_ratio,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )

        return api_response(
            data=result["items"],
            meta={
                "total": result["total"],
                "limit": result["limit"],
                "offset": result["offset"],
            },
        )

    @bp.route("/<code>", methods=["GET"])
    def get_etf(code: str):
        """Get ETF details by code.

        GET /api/v1/etfs/{code}

        Args:
            code: ETF code (4 digits)

        Returns:
            ETF details or 404 error
        """
        is_valid, error = validate_etf_code(code)
        if not is_valid:
            return error_response(error, 400)

        service = ETFService()
        etf = service.get_by_code(code)

        if not etf:
            return error_response("ETF not found", 404)

        return api_response(data=etf)

    @bp.route("/<code>/chart", methods=["GET"])
    def get_etf_chart(code: str):
        """Get chart data for an ETF.

        GET /api/v1/etfs/{code}/chart

        Args:
            code: ETF code (4 digits)

        Query Parameters:
            period: Time period (1w, 1m, 3m, 6m, 1y, 3y). Default: 1m

        Returns:
            Chart data or 404 error
        """
        is_valid, error = validate_etf_code(code)
        if not is_valid:
            return error_response(error, 400)

        period = request.args.get("period", "1m")

        service = ChartService()
        chart_data = service.get_chart_data(code, period)

        if not chart_data:
            return error_response("ETF not found", 404)

        return api_response(data=chart_data)

    return bp
