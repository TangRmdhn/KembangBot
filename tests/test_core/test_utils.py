"""Tests for utility functions."""

import pytest

from app.core.utils import (
    mask_phone,
    clean_phone,
    to_waha_chat_id,
    generate_short_id,
    safe_json_loads,
)


def test_mask_phone():
    """Test phone number masking."""
    assert mask_phone("6281234567890@c.us") == "62812****7890"


def test_mask_phone_short():
    """Test masking short phone numbers."""
    assert mask_phone("1234@c.us") == "****"


def test_clean_phone():
    """Test removing @c.us suffix."""
    assert clean_phone("6281234567890@c.us") == "6281234567890"
    assert clean_phone("6281234567890") == "6281234567890"


def test_to_waha_chat_id():
    """Test converting to WAHA chat ID format."""
    assert to_waha_chat_id("6281234567890") == "6281234567890@c.us"
    assert to_waha_chat_id("6281234567890@c.us") == "6281234567890@c.us"


def test_generate_short_id():
    """Test short ID generation."""
    short_id = generate_short_id("LEAD-")
    assert short_id.startswith("LEAD-")
    assert len(short_id) == 11  # "LEAD-" + 6 chars

    no_prefix = generate_short_id()
    assert len(no_prefix) == 6


def test_safe_json_loads_valid():
    """Test parsing valid JSON."""
    assert safe_json_loads('{"key": "value"}') == {"key": "value"}
    assert safe_json_loads('[1, 2, 3]') == [1, 2, 3]


def test_safe_json_loads_invalid():
    """Test parsing invalid JSON returns default."""
    assert safe_json_loads('invalid', default={}) == {}
    assert safe_json_loads('invalid', default=None) is None
    assert safe_json_loads(None, default="fallback") == "fallback"
