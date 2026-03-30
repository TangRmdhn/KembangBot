"""Integration tests for the LangGraph conversation graph."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.graph import invoke_conversation_graph, human_handoff_node


class MockConversation:
    """Mock conversation model for testing."""

    def __init__(self, customer_phone="6281234567890@c.us", current_stage="greeting"):
        self.customer_phone = customer_phone
        self.current_stage = current_stage
        self.collected_fields = {}
        self.messages = []


@pytest.mark.asyncio
async def test_full_graph_invocation():
    """Test that the full graph can be invoked and returns a formatted output."""
    conversation = MockConversation()

    with patch("app.agents.graph._graph") as mock_graph:
        mock_result = {
            "formatted_output": "Halo Kak! Ada yang bisa dibantu?",
            "current_stage": "greeting",
            "needs_human_handoff": False,
            "collected_fields": {},
        }
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        result = await invoke_conversation_graph(
            tenant_id="test-tenant-uuid",
            conversation=conversation,
            message_text="Halo, saya mau tanya tentang produk kalian",
        )

        assert result["formatted_output"] == "Halo Kak! Ada yang bisa dibantu?"


@pytest.mark.asyncio
async def test_graph_handles_human_handoff():
    """Test that graph handles human handoff request correctly."""
    conversation = MockConversation()

    with patch("app.agents.graph._graph") as mock_graph:
        mock_result = {
            "formatted_output": (
                "Baik Kak, saya akan hubungkan dengan tim kami ya. Mohon tunggu sebentar 🙏"
            ),
            "current_stage": "greeting",
            "needs_human_handoff": True,
            "handoff_reason": "customer_requested",
        }
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        result = await invoke_conversation_graph(
            tenant_id="test-tenant-uuid",
            conversation=conversation,
            message_text="Saya mau bicara dengan owner langsung",
        )

        assert result["needs_human_handoff"] is True
        assert "tim kami" in result["formatted_output"]


@pytest.mark.asyncio
async def test_graph_error_recovery():
    """Test that graph recovers gracefully from errors."""
    conversation = MockConversation()

    with patch("app.agents.graph._graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph invocation failed"))

        result = await invoke_conversation_graph(
            tenant_id="test-tenant-uuid",
            conversation=conversation,
            message_text="Halo",
        )

        # Should return fallback message, not crash
        assert "Maaf, terjadi gangguan" in result["formatted_output"]


@pytest.mark.asyncio
async def test_human_handoff_node():
    """Test the human handoff node directly."""
    state = {
        "tenant_id": "test-tenant",
        "current_stage": "greeting",
        "needs_human_handoff": True,
        "handoff_reason": "customer_requested",
    }

    result = await human_handoff_node(state)

    assert "tim kami" in result["formatted_output"]
    assert "🙏" in result["formatted_output"]


@pytest.mark.asyncio
async def test_graph_preserves_collected_fields():
    """Test that graph preserves collected fields across invocations."""
    conversation = MockConversation()
    conversation.collected_fields = {"event_type": "wedding", "date": "10 Mei 2026"}

    with patch("app.agents.graph._graph") as mock_graph:
        mock_result = {
            "formatted_output": "Baik Kak, untuk wedding di tanggal 10 Mei 2026...",
            "current_stage": "needs_check",
            "collected_fields": {"event_type": "wedding", "date": "10 Mei 2026"},
        }
        mock_graph.ainvoke = AsyncMock(return_value=mock_result)

        result = await invoke_conversation_graph(
            tenant_id="test-tenant-uuid",
            conversation=conversation,
            message_text="Tanggal 10 Mei 2026",
        )

        assert result["collected_fields"]["event_type"] == "wedding"
        assert result["collected_fields"]["date"] == "10 Mei 2026"
