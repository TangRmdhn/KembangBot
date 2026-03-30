"""Response formatter for LangGraph conversation engine.

The response formatter is the last node before the response is sent to
the customer. It applies brand-level formatting: adjusting tone, limiting
emojis, sanitizing technical leaks, and converting to WhatsApp format.
"""

import re
from loguru import logger

from app.agents.state import ConversationState


def _sanitize_technical_leaks(text: str) -> str:
    """Remove technical terms that might leak from LLM reasoning.

    Args:
        text: Raw text that may contain technical leaks.

    Returns:
        Sanitized text with technical terms removed or replaced.
    """
    # Replace technical phrases with natural alternatives
    replacements = {
        r"berdasarkan data kami": "dari informasi yang kami punya",
        r"berdasarkan database": "dari informasi yang kami punya",
        r"saya sebagai AI": "",
        r"saya sebagai bot": "",
        r"saya sebagai asisten virtual": "",
        r"saya adalah AI": "",
        r"saya adalah bot": "",
    }

    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Remove JSON-like patterns (technical leaks)
    text = re.sub(r"\{[^{}]*\}", "", text)

    # Remove technical terms when used in technical context
    technical_terms = [
        r"\btool_call\b",
        r"\bfunction_call\b",
        r"\bsearch_catalog\b",
        r"\bstage\b",
        r"\bfield\b",
        r"\bnode\b",
        r"\bgraph\b",
    ]

    for term in technical_terms:
        text = re.sub(term, "", text, flags=re.IGNORECASE)

    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _enforce_emoji_limit(text: str, max_emojis: int = 3) -> str:
    """Limit the number of emojis in text.

    Args:
        text: Text that may contain emojis.
        max_emojis: Maximum number of emojis to keep.

    Returns:
        Text with excess emojis removed.
    """
    # Unicode emoji pattern (covers most common emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "]+",
        flags=re.UNICODE,
    )

    # Find all emojis
    emojis = emoji_pattern.findall(text)
    total_emojis = len(emojis)

    if total_emojis <= max_emojis:
        return text

    # Remove excess emojis from the end
    emojis_to_remove = total_emojis - max_emojis
    emoji_positions = [(m.start(), m.end()) for m in emoji_pattern.finditer(text)]

    # Remove from the end backwards
    for start, end in reversed(emoji_positions[-emojis_to_remove:]):
        text = text[:start] + text[end:]

    return text


def _truncate_to_limit(text: str, max_chars: int = 1000) -> str:
    """Truncate text to max_chars at sentence boundary.

    Args:
        text: Text to truncate.
        max_chars: Maximum character count.

    Returns:
        Truncated text ending at sentence boundary with "..." if truncated.
    """
    if len(text) <= max_chars:
        return text

    # Find last sentence boundary before max_chars
    truncated = text[:max_chars]
    last_boundary = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
        truncated.rfind("\n"),
    )

    if last_boundary > max_chars * 0.5:  # Only truncate if we find a boundary in first half
        truncated = truncated[:last_boundary + 1]
    else:
        truncated = truncated.rsplit(" ", 1)[0]  # Fallback to word boundary

    return truncated.rstrip() + "..."


def _convert_markdown_to_whatsapp(text: str) -> str:
    """Convert Markdown formatting to WhatsApp formatting.

    Args:
        text: Text with Markdown formatting.

    Returns:
        Text with WhatsApp-compatible formatting.
    """
    # Bold: **text** -> *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Italic: __text__ -> _text_
    text = re.sub(r"__(.+?)__", r"_\1_", text)

    # Headings: # text -> *text*
    text = re.sub(r"^#\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^##\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"^###\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # List items: - item -> • item
    text = re.sub(r"^-\s+(.+)$", r"• \1", text, flags=re.MULTILINE)

    # Links: [text](url) -> text (url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)

    return text


async def formatter_node(state: ConversationState) -> dict:
    """Format the agent output for WhatsApp delivery.

    This function:
    1. Gets the raw agent output
    2. Applies formatting rules (length, emoji limit, sanitization)
    3. Converts Markdown to WhatsApp format
    4. Returns the formatted output

    Args:
        state: Current conversation state.

    Returns:
        Dict with formatted_output.
    """
    raw_output = state["agent_output"]
    tenant_id = state["tenant_id"]

    logger.info(
        "Formatter processing response",
        tenant_id=tenant_id,
        raw_length=len(raw_output),
    )

    # Apply formatting rules in order
    text = raw_output

    # 1. Sanitize technical leaks
    text = _sanitize_technical_leaks(text)

    # 2. Convert Markdown to WhatsApp format
    text = _convert_markdown_to_whatsapp(text)

    # 3. Enforce emoji limit
    text = _enforce_emoji_limit(text, max_emojis=3)

    # 4. Truncate to max length
    text = _truncate_to_limit(text, max_chars=1000)

    logger.info(
        "Formatter completed",
        tenant_id=tenant_id,
        formatted_length=len(text),
    )

    return {"formatted_output": text}
