"""Supervisor node for LangGraph conversation engine.

The supervisor is the routing brain of the LangGraph graph. It receives
every incoming message first, classifies intent, tracks stage progress,
extracts structured fields from conversation, and decides which node to
route to next. It does NOT generate customer-facing responses.
"""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.agents.state import ConversationState
from app.agents.prompts import build_field_extraction_prompt, build_intent_classification_prompt
from app.core.model_config import supervisor_llm


async def _extract_fields_from_response(
    llm,
    missing_fields: list[str],
    agent_response: str,
    customer_message: str,
) -> dict:
    """Extract structured fields from the latest message exchange.

    Args:
        llm: The LLM instance for extraction.
        missing_fields: List of fields we're looking for.
        agent_response: The agent's previous response.
        customer_message: The customer's latest message.

    Returns:
        Dict of extracted fields, or empty dict if extraction fails.
    """
    prompt = build_field_extraction_prompt(
        missing_fields=missing_fields,
        agent_response=agent_response,
        customer_message=customer_message,
    )

    try:
        messages = [SystemMessage(content=prompt), HumanMessage(content=customer_message)]
        response = await llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON response
        try:
            extracted = json.loads(content)
            if not isinstance(extracted, dict):
                logger.warning(
                    "Field extraction returned non-dict JSON",
                    content=content[:200],
                )
                return {}
            return extracted
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse field extraction JSON",
                content=content[:200],
            )
            return {}

    except Exception as e:
        logger.warning(
            "Field extraction LLM call failed",
            error=str(e),
        )
        return {}


def _compute_missing_fields(
    required_fields: list[str],
    collected_fields: dict,
) -> list[str]:
    """Compute which required fields are still missing.

    Args:
        required_fields: List of field names required for current stage.
        collected_fields: Dict of already collected field values.

    Returns:
        List of field names that are still missing or have empty values.
    """
    missing = []
    for field in required_fields:
        if field not in collected_fields:
            missing.append(field)
        elif collected_fields[field] is None or collected_fields[field] == "":
            missing.append(field)
    return missing


async def supervisor_node(state: ConversationState) -> dict:
    """Supervisor node that processes incoming messages and routes appropriately.

    This function:
    1. Gets the current stage config
    2. Extracts fields from the latest message exchange
    3. Checks stage transition conditions
    4. Classifies intent of the latest human message
    5. Returns updated state with routing decisions

    Args:
        state: Current conversation state.

    Returns:
        State update dict with: current_stage, collected_fields, missing_fields,
        needs_human_handoff, handoff_reason
    """
    tenant_id = state["tenant_id"]
    current_stage = state["current_stage"]
    stage_config = state["stage_config"]
    collected_fields = state["collected_fields"]
    missing_fields = state["missing_fields"]
    chat_history = state["chat_history"]

    logger.info(
        "Supervisor processing message",
        tenant_id=tenant_id,
        stage=current_stage,
        missing_fields=missing_fields,
    )

    # Get current stage config
    stages = stage_config.get("stages", {})
    current_stage_config = stages.get(current_stage, {})
    required_fields = current_stage_config.get("required_fields", [])

    # Extract fields from latest message exchange (if there are at least 2 messages)
    if len(chat_history) >= 2:
        # Get the last AI response and last human message
        last_human = None
        last_ai = None
        for msg in reversed(chat_history):
            if isinstance(msg, HumanMessage) and last_human is None:
                last_human = msg
            elif isinstance(msg, AIMessage) and last_ai is None:
                last_ai = msg
            if last_human and last_ai:
                break

        if last_human and last_ai:
            extracted = await _extract_fields_from_response(
                supervisor_llm,
                missing_fields or required_fields,
                last_ai.content,
                last_human.content,
            )

            # Merge extracted fields into collected_fields
            if extracted:
                collected_fields = {**collected_fields, **extracted}
                logger.info(
                    "Fields extracted from conversation",
                    tenant_id=tenant_id,
                    extracted_fields=list(extracted.keys()),
                )

    # Recompute missing fields
    missing_fields = _compute_missing_fields(required_fields, collected_fields)

    # Check stage transition: if all fields collected AND there's a next_stage
    next_stage = current_stage_config.get("next_stage")
    if not missing_fields and next_stage:
        old_stage = current_stage
        current_stage = next_stage
        logger.info(
            "Stage transition",
            tenant_id=tenant_id,
            from_stage=old_stage,
            to_stage=current_stage,
        )

        # Load new stage's required fields
        new_stage_config = stages.get(current_stage, {})
        new_required_fields = new_stage_config.get("required_fields", [])
        missing_fields = _compute_missing_fields(new_required_fields, collected_fields)

    # Classify intent of latest human message
    intent = "unknown"
    if chat_history:
        last_human_msg = None
        for msg in reversed(chat_history):
            if isinstance(msg, HumanMessage):
                last_human_msg = msg
                break

        if last_human_msg:
            intent_prompt = build_intent_classification_prompt()
            try:
                messages = [
                    SystemMessage(content=intent_prompt),
                    HumanMessage(content=last_human_msg.content),
                ]
                response = await supervisor_llm.ainvoke(messages)
                intent = response.content.strip().lower()
                logger.info(
                    "Intent classified",
                    tenant_id=tenant_id,
                    intent=intent,
                )
            except Exception as e:
                logger.warning(
                    "Intent classification failed",
                    tenant_id=tenant_id,
                    error=str(e),
                )
                intent = "unknown"

    # Check for human handoff
    needs_human_handoff = False
    handoff_reason = ""

    if intent == "human_handoff":
        needs_human_handoff = True
        handoff_reason = "customer_requested"
        logger.info(
            "Human handoff requested",
            tenant_id=tenant_id,
            reason=handoff_reason,
        )

    return {
        "current_stage": current_stage,
        "collected_fields": collected_fields,
        "missing_fields": missing_fields,
        "needs_human_handoff": needs_human_handoff,
        "handoff_reason": handoff_reason,
    }


def supervisor_router(state: ConversationState) -> str:
    """Route to the next node based on supervisor's decision.

    Args:
        state: Current conversation state.

    Returns:
        Node name to route to: "conversation_agent" or "human_handoff"
    """
    if state["needs_human_handoff"]:
        return "human_handoff"
    return "conversation_agent"
