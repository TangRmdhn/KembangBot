"""Tests for the conversation agent node."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.conversation import conversation_agent_node


@pytest.mark.asyncio
async def test_conversation_agent_returns_response(sample_state):
    """Test that conversation agent returns a response."""
    mock_response = AIMessage(content="Halo Kak! Ada yang bisa dibantu?")

    with patch("app.agents.conversation.agent_llm") as mock_llm:
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await conversation_agent_node(sample_state)

        assert result["agent_output"] == "Halo Kak! Ada yang bisa dibantu?"


@pytest.mark.asyncio
async def test_conversation_agent_appends_to_chat_history(sample_state):
    """Test that conversation agent appends AIMessage to chat history."""
    mock_response = AIMessage(content="Halo Kak! Ada yang bisa dibantu?")

    with patch("app.agents.conversation.agent_llm") as mock_llm:
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await conversation_agent_node(sample_state)

        assert len(result["chat_history"]) == 1
        assert isinstance(result["chat_history"][0], AIMessage)
        assert result["chat_history"][0].content == "Halo Kak! Ada yang bisa dibantu?"


@pytest.mark.asyncio
async def test_conversation_agent_handles_tool_calls(sample_state):
    """Test that conversation agent handles tool calls correctly."""
    # First response with tool call
    tool_call_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_catalog",
                "args": {"query": "paket wedding", "tenant_id": "test-tenant-uuid-123"},
                "id": "call_123",
            }
        ],
    )

    # Final response after tool execution
    final_response = AIMessage(
        content="Berikut adalah paket wedding yang kami rekomendasikan..."
    )

    with patch("app.agents.conversation.agent_llm") as mock_llm:
        mock_llm.bind_tools.return_value = mock_llm
        # First call returns tool call, second returns final response
        mock_llm.ainvoke = AsyncMock(side_effect=[tool_call_response, final_response])

        result = await conversation_agent_node(sample_state)

        assert "paket wedding" in result["agent_output"].lower()


@pytest.mark.asyncio
async def test_conversation_agent_fallback_on_error(sample_state):
    """Test that conversation agent returns fallback message on error."""
    with patch("app.agents.conversation.agent_llm") as mock_llm:
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM connection failed"))

        result = await conversation_agent_node(sample_state)

        assert "Maaf, saya sedang mengalami gangguan" in result["agent_output"]
