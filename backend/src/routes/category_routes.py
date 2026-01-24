"""Category API routes."""
from flask import Blueprint

from src.services import CategoryService
from src.utils import api_response, error_response


def create_category_bp():
    """Create category blueprint."""
    bp = Blueprint("categories", __name__, url_prefix="/categories")

    @bp.route("", methods=["GET"])
    def get_categories():
        """Get all categories.

        GET /api/v1/categories

        Returns:
            List of all categories sorted by sort_order
        """
        service = CategoryService()
        categories = service.get_all()

        return api_response(data=categories)

    @bp.route("/<int:category_id>", methods=["GET"])
    def get_category(category_id: int):
        """Get category by ID.

        GET /api/v1/categories/{category_id}

        Args:
            category_id: Category ID

        Returns:
            Category details or 404 error
        """
        service = CategoryService()
        category = service.get_by_id(category_id)

        if not category:
            return error_response("Category not found", 404)

        return api_response(data=category)

    return bp
