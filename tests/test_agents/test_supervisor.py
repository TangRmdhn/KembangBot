"""Tests for the supervisor node."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.supervisor import supervisor_node, supervisor_router, _compute_missing_fields


@pytest.mark.asyncio
async def test_supervisor_extracts_fields(sample_state):
    """Test that supervisor extracts fields from conversation."""
    mock_extracted = {"date": "10 Mei 2026"}

    with patch("app.agents.supervisor._extract_fields_from_response") as mock_extract:
        mock_extract.return_value = mock_extracted
        result = await supervisor_node(sample_state)

        assert result["collected_fields"] == {
            "event_type": "wedding",
            "date": "10 Mei 2026",
        }
        assert "date" not in result["missing_fields"]


@pytest.mark.asyncio
async def test_supervisor_computes_missing_fields(sample_state):
    """Test missing fields computation."""
    # Manually test the helper function
    required = ["a", "b", "c"]
    collected = {"a": "x"}
    missing = _compute_missing_fields(required, collected)

    assert missing == ["b", "c"]


@pytest.mark.asyncio
async def test_supervisor_transitions_stage(completed_stage_state):
    """Test that supervisor transitions stage when all fields collected."""
    result = await supervisor_node(completed_stage_state)

    assert result["current_stage"] == "offer_paket"
    assert result["missing_fields"] == ["package_selection"]


@pytest.mark.asyncio
async def test_supervisor_no_transition_when_fields_missing(sample_state):
    """Test that supervisor doesn't transition when fields are still missing."""
    result = await supervisor_node(sample_state)

    assert result["current_stage"] == "needs_check"
    assert len(result["missing_fields"]) > 0


@pytest.mark.asyncio
async def test_supervisor_detects_human_handoff(sample_state):
    """Test that supervisor detects human handoff request."""
    # Add a human handoff message to chat history
    sample_state["chat_history"].append(
        HumanMessage(content="Saya mau bicara dengan owner langsung")
    )

    with patch("app.agents.supervisor.supervisor_llm") as mock_llm:
        mock_response = MagicMock()
        mock_response.content = "human_handoff"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        result = await supervisor_node(sample_state)

        assert result["needs_human_handoff"] is True
        assert result["handoff_reason"] == "customer_requested"


@pytest.mark.asyncio
async def test_supervisor_handles_malformed_json(sample_state):
    """Test that supervisor handles malformed JSON gracefully."""
    with patch("app.agents.supervisor._extract_fields_from_response") as mock_extract:
        mock_extract.return_value = {}  # Simulate failed extraction
        result = await supervisor_node(sample_state)

        # Should not crash, should return empty dict
        assert result["collected_fields"] == {"event_type": "wedding"}


def test_supervisor_router_routes_to_agent(sample_state):
    """Test that supervisor router routes to conversation_agent by default."""
    route = supervisor_router(sample_state)
    assert route == "conversation_agent"


def test_supervisor_router_routes_to_handoff(sample_state):
    """Test that supervisor router routes to human_handoff when flag is set."""
    sample_state["needs_human_handoff"] = True
    route = supervisor_router(sample_state)
    assert route == "human_handoff"
