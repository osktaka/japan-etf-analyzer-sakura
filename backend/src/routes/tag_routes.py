"""Tag API routes."""
from flask import Blueprint

from src.services import TagService
from src.utils import api_response, error_response


def create_tag_bp():
    """Create tag blueprint."""
    bp = Blueprint("tags", __name__, url_prefix="/tags")

    @bp.route("", methods=["GET"])
    def get_tags():
        """Get all tags.

        GET /api/v1/tags

        Returns:
            List of all tags sorted by name
        """
        service = TagService()
        tags = service.get_all()

        return api_response(data=tags)

    @bp.route("/<int:tag_id>", methods=["GET"])
    def get_tag(tag_id: int):
        """Get tag by ID.

        GET /api/v1/tags/{tag_id}

        Args:
            tag_id: Tag ID

        Returns:
            Tag details or 404 error
        """
        service = TagService()
        tag = service.get_by_id(tag_id)

        if not tag:
            return error_response("Tag not found", 404)

        return api_response(data=tag)

    return bp
