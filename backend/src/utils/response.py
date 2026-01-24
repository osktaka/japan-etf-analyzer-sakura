"""Response helper functions."""
from typing import Dict, List, Optional, Union

from flask import jsonify


def api_response(
    data: Union[Dict, List, None] = None,
    message: Optional[str] = None,
    status_code: int = 200,
    meta: Optional[Dict] = None,
):
    """Create a standardized API response."""
    response = {"success": True}

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if meta:
        response["meta"] = meta

    return jsonify(response), status_code


def error_response(
    message: str,
    status_code: int = 400,
    errors: Optional[List[Dict]] = None,
):
    """Create a standardized error response."""
    response = {
        "success": False,
        "error": {
            "message": message,
            "code": status_code,
        },
    }

    if errors:
        response["error"]["details"] = errors

    return jsonify(response), status_code
