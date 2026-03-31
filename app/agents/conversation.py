"""Conversation agent node for LangGraph engine.

The conversation agent is the node that actually talks to the customer.
It generates natural Bahasa Indonesia responses based on the current stage
instructions, collected data, and available tools.
"""

from loguru import logger
from langchain_core.messages import (
    SystemMessage,
    AIMessage,
    ToolMessage,
    HumanMessage,
)

from app.agents.state import ConversationState
from app.agents.prompts import build_system_prompt
from app.agents.tools import get_tools
from app.core.model_config import agent_llm


async def conversation_agent_node(state: ConversationState) -> dict:
    """Main conversation agent node that generates responses to customers.

    This function:
    1. Loads stage-specific context
    2. Builds the system prompt with tenant config
    3. Prepares message list with chat history
    4. Invokes the LLM with tools bound
    5. Handles tool calls with a simple execution loop
    6. Returns the response and updated chat history

    Args:
        state: Current conversation state.

    Returns:
        Dict with agent_output and chat_history update.
    """
    tenant_id = state["tenant_id"]
    current_stage = state["current_stage"]
    stage_config = state["stage_config"]
    collected_fields = state["collected_fields"]
    missing_fields = state["missing_fields"]
    chat_history = state["chat_history"]

    # Get stage-specific config
    stages = stage_config.get("stages", {})
    current_stage_config = stages.get(current_stage, {})

    # Extract tenant config fields
    agent_name = current_stage_config.get("agent_name", "Asisten Penjualan")
    business_name = current_stage_config.get("business_name", "bisnis kami")
    brand_voice = current_stage_config.get("brand_voice", "ramah dan profesional")
    stage_instructions = current_stage_config.get("instructions", "")
    stage_goal = current_stage_config.get("goal", "")

    logger.info(
        "Invoking conversation agent",
        tenant_id=tenant_id,
        stage=current_stage,
        tools_count=len(get_tools()),
    )

    # Build system prompt
    system_prompt = build_system_prompt(
        agent_name=agent_name,
        business_name=business_name,
        brand_voice=brand_voice,
        current_stage=current_stage,
        stage_instructions=stage_instructions,
        stage_goal=stage_goal,
        collected_fields=collected_fields,
        missing_fields=missing_fields,
        tenant_id=tenant_id,
    )

    # Prepare messages: system prompt + chat history
    messages = [SystemMessage(content=system_prompt)] + chat_history

    # Bind tools to LLM
    tools = get_tools()
    llm_with_tools = agent_llm.bind_tools(tools)

    # Tool execution loop (max 3 iterations)
    max_iterations = 3
    iteration = 0

    try:
        while iteration < max_iterations:
            iteration += 1

            # Invoke LLM
            response = await llm_with_tools.ainvoke(messages)

            # Check if there are tool calls
            if not hasattr(response, "tool_calls") or not response.tool_calls:
                # No tool calls, we have the final response
                break

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "")

                logger.info(
                    "Tool called",
                    tenant_id=tenant_id,
                    tool_name=tool_name,
                    args=str(tool_args)[:100],
                )

                # Find and execute the tool
                tool_result = None
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            # Inject tenant_id into tool args if needed
                            if "tenant_id" not in tool_args:
                                tool_args["tenant_id"] = tenant_id
                            tool_result = await tool.ainvoke(tool_args)
                        except Exception as e:
                            logger.error(
                                "Tool execution failed",
                                tenant_id=tenant_id,
                                tool_name=tool_name,
                                error=str(e),
                            )
                            tool_result = f"Error executing tool: {str(e)}"
                        break

                if tool_result is None:
                    tool_result = f"Unknown tool: {tool_name}"

                # Add tool result to messages
                messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_id))

            # Add the AI's tool call response to messages for context
            messages.append(AIMessage(content=response.content, tool_calls=response.tool_calls))

        # Final response
        final_content = response.content

        logger.info(
            "Conversation agent completed",
            tenant_id=tenant_id,
            response_length=len(final_content),
        )

        return {
            "agent_output": final_content,
            "chat_history": [AIMessage(content=final_content)],
        }

    except Exception as e:
        logger.error(
            "Conversation agent failed",
            tenant_id=tenant_id,
            error=str(e),
            exc_info=True,
        )

        # Fallback message in Indonesian
        fallback_message = "Maaf, saya sedang mengalami gangguan. Bisa coba kirim pesan lagi sebentar? 🙏"
        return {
            "agent_output": fallback_message,
            "chat_history": [AIMessage(content=fallback_message)],
        }
