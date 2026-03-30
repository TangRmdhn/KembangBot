"""Conversation state definitions for LangGraph engine.

This module defines the shared state structure that all LangGraph nodes
read from and write to during conversation processing.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    """Shared state for the LangGraph conversation engine.

    This TypedDict defines the structure of state that flows through
    all nodes in the conversation graph. Each node reads from and writes
    to this state, with specific update semantics for each field.

    Attributes:
        tenant_id: UUID string of the business tenant. Set once at graph
            invocation and never changes during the conversation.
        customer_phone: WhatsApp phone in format "6281234567890@c.us".
            Set once and never changes.
        current_stage: Active stage ID from tenant's flow config
            (e.g., "greeting", "needs_check", "booking"). Initialized from
            DB, updated by supervisor when stage transitions occur.
        collected_fields: Key-value pairs of data gathered from customer
            so far. Example: {"event_type": "wedding", "date": "2026-05-10",
            "location": "Jogja"}. Updated by supervisor after extracting
            fields from agent output. REPLACES on update (not append).
        missing_fields: Field names still needed before current stage can
            transition. Computed by supervisor: required_fields - collected_fields.keys().
            REPLACES on update.
        chat_history: Full conversation as LangChain messages (HumanMessage,
            AIMessage). Uses add_messages reducer — returning new messages
            APPENDS, does not replace.
        stage_config: Tenant's full stage flow config loaded from DB/Redis
            before graph invocation. READ-ONLY within the graph. Never
            modified by any node. Structure: {"stages": {"greeting":
            {"goal": "...", "instructions": "...", ...}}, "initial_stage": "greeting"}
        agent_output: Raw text output from the conversation agent, before
            formatting. Set by conversation agent node, read by formatter node.
        formatted_output: Final formatted response to send to customer.
            Set by formatter node, read by the graph invoker to send via WAHA.
        needs_human_handoff: Flag set by any node when conversation should
            be transferred to a human. Defaults to False.
        handoff_reason: Explanation for why handoff was triggered.
            Examples: "customer_requested", "low_confidence", "angry_customer",
            "out_of_scope". Only meaningful when needs_human_handoff is True.
    """

    tenant_id: str
    customer_phone: str
    current_stage: str
    collected_fields: dict
    missing_fields: list[str]
    # Uses add_messages reducer - new messages append to existing history
    chat_history: Annotated[list[BaseMessage], add_messages]
    # READ-ONLY: never modified by graph nodes
    stage_config: dict
    agent_output: str
    formatted_output: str
    needs_human_handoff: bool
    handoff_reason: str
