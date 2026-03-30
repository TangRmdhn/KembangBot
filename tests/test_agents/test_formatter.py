"""Tests for the formatter node."""

import pytest
from langchain_core.messages import AIMessage

from app.agents.formatter import (
    formatter_node,
    _sanitize_technical_leaks,
    _enforce_emoji_limit,
    _truncate_to_limit,
    _convert_markdown_to_whatsapp,
)


def test_truncate_long_response():
    """Test truncation of long responses at sentence boundary."""
    long_text = "Kalimat pertama. Kalimat kedua. " * 100  # ~2800 chars
    result = _truncate_to_limit(long_text, max_chars=1000)

    assert len(result) <= 1010  # Allow for "..."
    assert result.endswith("...")


def test_truncate_short_response():
    """Test that short responses pass through unchanged."""
    short_text = "Halo Kak! Ada yang bisa dibantu?"
    result = _truncate_to_limit(short_text, max_chars=1000)

    assert result == short_text


def test_emoji_limit_enforced():
    """Test that excess emojis are removed."""
    text_with_many_emojis = "Halo Kak! 😊😊😊😊😊😊😊😊😊😊"
    result = _enforce_emoji_limit(text_with_many_emojis, max_emojis=3)

    emoji_count = result.count("😊")
    assert emoji_count <= 3


def test_sanitize_ai_mention():
    """Test that AI self-mentions are removed."""
    text = "Saya sebagai AI akan membantu Kakak"
    result = _sanitize_technical_leaks(text)

    assert "sebagai AI" not in result


def test_sanitize_json_leak():
    """Test that JSON leaks are removed."""
    text = 'Berikut hasilnya: {"tool": "search", "result": "found"} untuk Kakak'
    result = _sanitize_technical_leaks(text)

    assert "{" not in result
    assert "}" not in result


def test_markdown_to_whatsapp_bold():
    """Test Markdown bold conversion."""
    markdown = "**Ini tebal** dan ini biasa"
    result = _convert_markdown_to_whatsapp(markdown)

    assert result == "*Ini tebal* dan ini biasa"


def test_markdown_to_whatsapp_italic():
    """Test Markdown italic conversion."""
    markdown = "__Ini miring__ dan ini biasa"
    result = _convert_markdown_to_whatsapp(markdown)

    assert result == "_Ini miring_ dan ini biasa"


def test_markdown_to_whatsapp_link():
    """Test Markdown link conversion."""
    markdown = "Kunjungi [website kami](http://example.com) untuk info lebih lanjut"
    result = _convert_markdown_to_whatsapp(markdown)

    assert result == "Kunjungi website kami (http://example.com) untuk info lebih lanjut"


def test_markdown_to_whatsapp_heading():
    """Test Markdown heading conversion."""
    markdown = "# Judul Utama"
    result = _convert_markdown_to_whatsapp(markdown)

    assert result == "*Judul Utama*"


def test_markdown_to_whatsapp_list():
    """Test Markdown list item conversion."""
    markdown = "- Item pertama\n- Item kedua"
    result = _convert_markdown_to_whatsapp(markdown)

    assert "• Item pertama" in result
    assert "• Item kedua" in result


def test_passthrough_clean_text():
    """Test that clean text passes through unchanged."""
    clean_text = "Halo Kak! Ada yang bisa saya bantu hari ini?"
    result = _sanitize_technical_leaks(clean_text)

    assert result == clean_text


@pytest.mark.asyncio
async def test_formatter_node_full_pipeline(sample_state):
    """Test the full formatter node pipeline."""
    sample_state["agent_output"] = (
        "**Halo Kak!** 😊😊😊😊😊 Saya sebagai AI akan membantu. "
        "Berikut info yang Kakak minta: {\"tool\": \"search\"}. "
        "Silakan cek website kami di [link](http://example.com) untuk detail lebih lanjut. "
        "Semoga membantu! 😊"
    )

    result = await formatter_node(sample_state)

    formatted = result["formatted_output"]

    # Should not contain technical leaks
    assert "sebagai AI" not in formatted
    assert "{" not in formatted
    assert "}" not in formatted

    # Should have WhatsApp formatting
    assert "*Halo Kak!*" in formatted
    assert "(http://example.com)" in formatted
