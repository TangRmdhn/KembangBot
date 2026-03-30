"""Kembang AI LangGraph conversation engine.

This package contains the LangGraph-based AI conversation engine that
handles customer interactions on WhatsApp. The engine uses a multi-node
graph architecture with:

- supervisor: Routes messages and extracts structured data
- conversation_agent: Generates natural responses with tool access
- formatter: Applies brand formatting and sanitizes output
- graph: Wires everything together into a compiled LangGraph

Usage:
    from app.agents.graph import invoke_conversation_graph
    
    result = await invoke_conversation_graph(
        tenant_id=tenant_id,
        conversation=conversation,
        message_text="Halo, saya mau tanya tentang produk kalian",
    )
    
    response = result["formatted_output"]
"""

from app.agents.state import ConversationState
from app.agents.graph import invoke_conversation_graph, build_graph

__all__ = [
    "ConversationState",
    "invoke_conversation_graph",
    "build_graph",
]
