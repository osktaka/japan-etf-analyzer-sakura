"""Compare routes for ETF performance comparison API."""
from flask import Blueprint, request

from src.services.compare_service import CompareService
from src.utils import api_response, error_response


def create_compare_bp() -> Blueprint:
    """Create compare blueprint."""
    bp = Blueprint("compare", __name__, url_prefix="/compare")
    service = CompareService()

    @bp.route("/performance", methods=["GET"])
    def get_performance():
        """Get performance comparison for multiple ETFs.

        Query params:
            codes: Comma-separated list of ETF codes

        Returns:
            Performance comparison data
        """
        codes_param = request.args.get("codes", "")
        if not codes_param:
            return error_response("codes parameter is required", 400)

        codes = [c.strip() for c in codes_param.split(",") if c.strip()]
        if not codes:
            return error_response("At least one code is required", 400)

        if len(codes) > 10:
            return error_response("Maximum 10 codes allowed", 400)

        comparison = service.get_comparison(codes)
        return api_response(data=comparison)

    @bp.route("/performance/<code>", methods=["GET"])
    def get_etf_performance(code: str):
        """Get performance metrics for a single ETF.

        Args:
            code: ETF code

        Returns:
            Performance metrics
        """
        performance = service.get_performance(code)
        return api_response(data=performance)

    return bp
