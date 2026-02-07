"""ETF API routes."""
from flask import Blueprint, request

from src.services import ChartService, CompareService, ETFService
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
            momentum_labels: Filter by momentum labels (comma-separated, e.g., "上昇加速,上昇維持")
            min_dividend_yield: Minimum dividend yield (%)
            max_expense_ratio: Maximum expense ratio (%)
            favorite_codes: Filter by favorite codes (comma-separated)
            holding_codes: Filter by holding codes (comma-separated)
            sort: Sort column (code, name, dividend_yield, expense_ratio, total_assets)
            order: Sort order (asc, desc). Default: asc
            return_type: Return type for performance sorting (price, regression). Default: price
            scoring_mode: Scoring mode - "full" (default) or "partial"
            perspective: Perspective ID for score calculation (balance, dividend, etc.). Default: balance
            custom_weights: JSON string of custom weights (e.g., {"dividend_power": 0.3, ...})
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
        favorite_codes_param = request.args.get("favorite_codes")
        holding_codes_param = request.args.get("holding_codes")
        sort = request.args.get("sort")
        order = request.args.get("order", "asc")
        return_type = request.args.get("return_type", "price")
        scoring_mode = request.args.get("scoring_mode", "full")
        perspective = request.args.get("perspective", "balance")
        custom_weights_param = request.args.get("custom_weights")

        if order not in ("asc", "desc"):
            return error_response("Invalid order parameter. Use 'asc' or 'desc'", 400)

        if return_type not in ("price", "regression"):
            return error_response(
                "Invalid return_type parameter. Use 'price' or 'regression'", 400
            )

        if scoring_mode not in ("full", "partial"):
            return error_response(
                "Invalid scoring_mode parameter. Use 'full' or 'partial'", 400
            )

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

        momentum_labels = None
        momentum_labels_param = request.args.get("momentum_labels")
        if momentum_labels_param:
            momentum_labels = [
                label.strip()
                for label in momentum_labels_param.split(",")
                if label.strip()
            ]

        favorite_codes = None
        if favorite_codes_param:
            favorite_codes = [
                code.strip() for code in favorite_codes_param.split(",") if code.strip()
            ]

        holding_codes = None
        if holding_codes_param:
            holding_codes = [
                code.strip() for code in holding_codes_param.split(",") if code.strip()
            ]

        custom_weights = None
        if custom_weights_param:
            try:
                import json
                custom_weights = json.loads(custom_weights_param)
            except (ValueError, json.JSONDecodeError):
                return error_response("Invalid custom_weights format", 400)

        service = ETFService()
        result = service.search(
            keyword=keyword,
            category_id=category_id,
            tag_ids=tag_ids,
            momentum_labels=momentum_labels,
            min_dividend_yield=min_dividend_yield,
            max_expense_ratio=max_expense_ratio,
            favorite_codes=favorite_codes,
            holding_codes=holding_codes,
            sort=sort,
            order=order,
            return_type=return_type,
            scoring_mode=scoring_mode,
            perspective=perspective,
            custom_weights=custom_weights,
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

    @bp.route("/performance/batch", methods=["GET"])
    def get_batch_performance():
        """Get performance metrics for multiple ETFs.

        GET /api/v1/etfs/performance/batch

        Query Parameters:
            codes: Comma-separated ETF codes (max 50)

        Returns:
            Performance data for each ETF
        """
        codes_param = request.args.get("codes", "")
        if not codes_param:
            return error_response("codes parameter is required", 400)

        codes = [c.strip() for c in codes_param.split(",") if c.strip()]
        if not codes:
            return error_response("At least one valid code is required", 400)

        if len(codes) > 50:
            return error_response("Maximum 50 codes allowed", 400)

        # Validate each code
        for code in codes:
            is_valid, error = validate_etf_code(code)
            if not is_valid:
                return error_response(f"Invalid code '{code}': {error}", 400)

        service = CompareService()
        result = service.get_batch_performance(codes)

        return api_response(data=result)

    @bp.route("/<code>/chart/batch", methods=["GET"])
    def get_etf_chart_batch(code: str):
        """Get chart data for a single ETF across multiple periods.

        GET /api/v1/etfs/{code}/chart/batch

        Args:
            code: ETF code (4 digits)

        Query Parameters:
            periods: Comma-separated periods (e.g., 3m,6m,1y,3y,5y,10y)

        Returns:
            Chart data for all requested periods or 404 error
        """
        is_valid, error = validate_etf_code(code)
        if not is_valid:
            return error_response(error, 400)

        periods_param = request.args.get("periods", "")
        if not periods_param:
            return error_response("periods parameter is required", 400)

        periods = [p.strip() for p in periods_param.split(",") if p.strip()]
        if not periods:
            return error_response("At least one valid period is required", 400)

        if len(periods) > 10:
            return error_response("Maximum 10 periods allowed", 400)

        service = ChartService()
        chart_data = service.get_batch_periods_chart_data(code, periods)

        if not chart_data:
            return error_response("ETF not found", 404)

        return api_response(data=chart_data)

    @bp.route("/chart/batch", methods=["GET"])
    def get_etfs_chart_batch():
        """Get chart data for multiple ETFs with a single period.

        GET /api/v1/etfs/chart/batch

        Query Parameters:
            codes: Comma-separated ETF codes (max 50)
            period: Time period (1m, 3m, 6m, 1y, 3y, 5y, 10y, 20y). Default: 1y

        Returns:
            Chart data for each requested ETF
        """
        codes_param = request.args.get("codes", "")
        if not codes_param:
            return error_response("codes parameter is required", 400)

        codes = [c.strip() for c in codes_param.split(",") if c.strip()]
        if not codes:
            return error_response("At least one valid code is required", 400)

        if len(codes) > 50:
            return error_response("Maximum 50 codes allowed", 400)

        # Validate each code
        for code in codes:
            is_valid, error = validate_etf_code(code)
            if not is_valid:
                return error_response(f"Invalid code '{code}': {error}", 400)

        period = request.args.get("period", "1y")

        service = ChartService()
        result = service.get_batch_codes_chart_data(codes, period)

        return api_response(data=result)

    @bp.route("/scores/batch", methods=["GET"])
    def get_batch_scores():
        """Get all 6 perspective scores for multiple ETFs.

        GET /api/v1/etfs/scores/batch

        Query Parameters:
            codes: Comma-separated ETF codes (max 100)
            scoring_mode: Scoring mode - "full" (default) or "partial"

        Returns:
            Scores for each requested ETF
        """
        codes_param = request.args.get("codes", "")
        if not codes_param:
            return error_response("codes parameter is required", 400)

        codes = [c.strip() for c in codes_param.split(",") if c.strip()]
        if not codes:
            return error_response("At least one valid code is required", 400)

        if len(codes) > 100:
            return error_response("Maximum 100 codes allowed", 400)

        scoring_mode = request.args.get("scoring_mode", "full")
        if scoring_mode not in ["full", "partial"]:
            scoring_mode = "full"

        # Validate each code
        for code in codes:
            is_valid, error = validate_etf_code(code)
            if not is_valid:
                return error_response(f"Invalid code '{code}': {error}", 400)

        service = ETFService()
        result = service.get_batch_scores(codes, scoring_mode)

        return api_response(data=result)

    return bp
