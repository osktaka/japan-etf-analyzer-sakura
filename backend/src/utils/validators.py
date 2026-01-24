"""Request validation functions."""
import re
from typing import Optional, Tuple


def validate_etf_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validate ETF code format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code:
        return False, "ETF code is required"

    if not re.match(r"^\d{4}$", code):
        return False, "ETF code must be 4 digits"

    return True, None


def validate_pagination(
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    max_limit: int = 100,
) -> Tuple[int, int, Optional[str]]:
    """Validate and normalize pagination parameters.

    Returns:
        Tuple of (validated_limit, validated_offset, error_message)
    """
    validated_limit = 50
    validated_offset = 0

    if limit is not None:
        try:
            validated_limit = int(limit)
            if validated_limit < 1:
                return 50, 0, "Limit must be positive"
            if validated_limit > max_limit:
                validated_limit = max_limit
        except (ValueError, TypeError):
            return 50, 0, "Limit must be a number"

    if offset is not None:
        try:
            validated_offset = int(offset)
            if validated_offset < 0:
                return validated_limit, 0, "Offset must be non-negative"
        except (ValueError, TypeError):
            return validated_limit, 0, "Offset must be a number"

    return validated_limit, validated_offset, None
