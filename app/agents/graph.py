"""LangGraph conversation graph builder and invocation.

This module wires together all nodes into a compiled LangGraph and
exposes the main invocation function that the webhook handler calls.
"""

from loguru import logger
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.agents.state import ConversationState
from app.agents.supervisor import supervisor_node, supervisor_router
from app.agents.conversation import conversation_agent_node
from app.agents.formatter import formatter_node


async def human_handoff_node(state: ConversationState) -> dict:
    """Simple node that handles human handoff scenario.

    Args:
        state: Current conversation state.

    Returns:
        Dict with formatted_output containing handoff message.
    """
    handoff_message = (
        "Baik Kak, saya akan hubungkan dengan tim kami ya. Mohon tunggu sebentar 🙏\n\n"
        "Tim kami akan segera menghubungi Kakak melalui WhatsApp ini."
    )

    return {"formatted_output": handoff_message}


def build_graph() -> "CompiledStateGraph":
    """Build and compile the LangGraph conversation graph.

    Graph structure:
        START
          │
          ▼
        supervisor ──(conditional)──┬── conversation_agent ── formatter ── END
                                    │
                                    └── human_handoff ── END

    Returns:
        Compiled LangGraph ready for invocation.
    """
    # Create state graph
    graph = StateGraph(ConversationState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("conversation_agent", conversation_agent_node)
    graph.add_node("formatter", formatter_node)
    graph.add_node("human_handoff", human_handoff_node)

    # Set entry point
    graph.add_edge(START, "supervisor")

    # Add conditional edges from supervisor
    graph.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "conversation_agent": "conversation_agent",
            "human_handoff": "human_handoff",
        },
    )

    # Add regular edges
    graph.add_edge("conversation_agent", "formatter")
    graph.add_edge("formatter", END)
    graph.add_edge("human_handoff", END)

    # Compile and return
    return graph.compile()


# Build graph once at module load (stateless and reusable)
_graph = build_graph()


def _load_chat_history(conversation) -> list[BaseMessage]:
    """Convert conversation's stored messages to LangChain message objects.

    Args:
        conversation: Conversation model from DB with messages attribute.

    Returns:
        List of LangChain BaseMessage objects, limited to last 20 messages.
    """
    messages = []
    conversation_messages = getattr(conversation, "messages", [])

    # Limit to last 20 messages
    for msg in conversation_messages[-20:]:
        role = getattr(msg, "role", "human")
        content = getattr(msg, "content", "")

        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))

    return messages


async def invoke_conversation_graph(
    tenant_id: str,
    conversation: any,
    message_text: str,
    stage_config: dict | None = None,
) -> dict:
    """Main entry point for invoking the conversation graph.

    This function is called by the webhook handler to process incoming
    customer messages through the LangGraph engine.

    Args:
        tenant_id: UUID string of the business tenant.
        conversation: Conversation model from DB containing customer info and history.
        message_text: The new incoming message text from the customer.
        stage_config: Optional pre-loaded stage config. If not provided,
            uses a placeholder config (TODO: integrate with StageService).

    Returns:
        Result dict containing the final state after all nodes have run,
        including formatted_output ready to send to customer.
    """
    customer_phone = getattr(conversation, "customer_phone", "")
    current_stage = getattr(conversation, "current_stage", "greeting")
    collected_fields = getattr(conversation, "collected_fields", {}) or {}

    logger.info(
        "Graph invocation started",
        tenant_id=tenant_id,
        stage=current_stage,
        message_length=len(message_text),
    )

    # TODO: integrate with StageService.get_flow_config(tenant_id)
    # For now, use placeholder config if not provided
    if stage_config is None:
        stage_config = {
            "stages": {
                "greeting": {
                    "agent_name": "Asisten Penjualan",
                    "business_name": "bisnis kami",
                    "brand_voice": "ramah dan profesional",
                    "goal": "Menyapa customer dan memulai percakapan",
                    "instructions": "Sapa customer dengan ramah, tanyakan apa yang bisa dibantu.",
                    "required_fields": [],
                    "next_stage": "needs_check",
                },
                "needs_check": {
                    "agent_name": "Asisten Penjualan",
                    "business_name": "bisnis kami",
                    "brand_voice": "ramah dan profesional",
                    "goal": "Mengumpulkan informasi kebutuhan customer",
                    "instructions": "Tanyakan detail kebutuhan customer untuk memberikan rekomendasi yang tepat.",
                    "required_fields": ["event_type", "date", "location"],
                    "next_stage": "booking",
                },
                "booking": {
                    "agent_name": "Asisten Penjualan",
                    "business_name": "bisnis kami",
                    "brand_voice": "ramah dan profesional",
                    "goal": "Menutup penjualan dan melakukan booking",
                    "instructions": "Konfirmasi detail dan arahkan customer untuk melakukan booking.",
                    "required_fields": ["package_selection", "payment_method"],
                    "next_stage": None,
                },
            },
            "initial_stage": "greeting",
        }

    # Build initial state
    initial_state = {
        "tenant_id": tenant_id,
        "customer_phone": customer_phone,
        "current_stage": current_stage,
        "collected_fields": collected_fields,
        "missing_fields": [],  # Will be computed by supervisor
        "chat_history": _load_chat_history(conversation)
        + [HumanMessage(content=message_text)],
        "stage_config": stage_config,
        "agent_output": "",
        "formatted_output": "",
        "needs_human_handoff": False,
        "handoff_reason": "",
    }

    try:
        # Invoke the graph
        result = await _graph.ainvoke(initial_state)

        logger.info(
            "Graph invocation completed",
            tenant_id=tenant_id,
            final_stage=result.get("current_stage", current_stage),
            needs_handoff=result.get("needs_human_handoff", False),
        )

        return result

    except Exception as e:
        logger.error(
            "Graph invocation failed",
            tenant_id=tenant_id,
            error=str(e),
            exc_info=True,
        )

        # Return fallback state on error
        return {
            "formatted_output": "Maaf, terjadi gangguan pada sistem kami. Silakan coba lagi dalam beberapa saat 🙏",
            "needs_human_handoff": False,
            "current_stage": current_stage,  # Don't change stage on error
            "collected_fields": collected_fields,  # Preserve data
        }
