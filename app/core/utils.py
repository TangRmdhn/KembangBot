"""Utility functions for Kembang AI.

Common helper functions used across the application.
"""

import json
import uuid
from typing import Any


def mask_phone(phone: str) -> str:
    """Mask phone number for logging purposes.

    Args:
        phone: Phone number in format "6281234567890@c.us".

    Returns:
        Masked phone number like "62812****7890".

    Example:
        >>> mask_phone("6281234567890@c.us")
        '62812****7890'
    """
    # Remove @c.us suffix if present
    clean = phone.replace("@c.us", "")

    if len(clean) < 9:
        return "****"

    # Keep first 5 and last 4, mask middle
    return f"{clean[:5]}****{clean[-4:]}"


def clean_phone(phone: str) -> str:
    """Extract clean phone number without suffix.

    Args:
        phone: Phone number in format "6281234567890@c.us".

    Returns:
        Clean phone number like "6281234567890".
    """
    return phone.replace("@c.us", "")


def to_waha_chat_id(phone: str) -> str:
    """Convert phone number to WAHA chat ID format.

    Args:
        phone: Phone number (with or without @c.us).

    Returns:
        Phone number in format "6281234567890@c.us".
    """
    clean = phone.replace("@c.us", "")
    return f"{clean}@c.us"


def generate_short_id(prefix: str = "") -> str:
    """Generate a short unique ID for display purposes.

    Args:
        prefix: Optional prefix to add before the ID.

    Returns:
        Short ID like "LEAD-A3F8B2" or "A3F8B2" if no prefix.

    Example:
        >>> generate_short_id("LEAD-")
        'LEAD-A3F8B2'
    """
    short_uuid = str(uuid.uuid4()).replace("-", "")[:6].upper()
    return f"{prefix}{short_uuid}" if prefix else short_uuid


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Parse JSON safely, returning default on failure.

    Args:
        text: JSON string to parse.
        default: Value to return if parsing fails.

    Returns:
        Parsed JSON object or default value.

    Example:
        >>> safe_json_loads('{"key": "value"}')
        {'key': 'value'}
        >>> safe_json_loads('invalid', default={})
        {}
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default
