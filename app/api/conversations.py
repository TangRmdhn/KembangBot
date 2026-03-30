"""Conversation API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from app.schemas.conversation import ConversationResponse, ConversationDetail, MessageResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.conversation import ConversationService
from app.dependencies import get_conversation_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("/", response_model=PaginatedResponse[ConversationResponse])
async def list_conversations(
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> PaginatedResponse[ConversationResponse]:
    """List conversations for tenant with filtering.

    Returns paginated list of conversations, optionally filtered by status.
    """
    conversations, total = await conversation_service.list_by_tenant(
        tenant_id=tenant_id,
        status=status,
        page=page,
        per_page=per_page,
    )

    return PaginatedResponse(
        success=True,
        data=[ConversationResponse.model_validate(c) for c in conversations],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.get("/{conversation_id}", response_model=APIResponse[ConversationDetail])
async def get_conversation(
    conversation_id: str,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[ConversationDetail]:
    """Get conversation with messages.

    Returns conversation details including all messages.
    """
    conversation = await conversation_service.get_by_id(conversation_id, tenant_id)
    messages = await conversation_service.get_chat_history(str(conversation.id))

    return APIResponse(
        success=True,
        data=ConversationDetail(
            **ConversationResponse.model_validate(conversation).model_dump(),
            messages=[MessageResponse.model_validate(m) for m in messages],
        ),
    )


@router.post("/{conversation_id}/handoff", response_model=APIResponse[dict])
async def trigger_handoff(
    conversation_id: str,
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[dict]:
    """Trigger human handoff for conversation.

    Marks the conversation for human agent takeover.
    """
    # Verify conversation exists for tenant
    await conversation_service.get_by_id(conversation_id, tenant_id)

    await conversation_service.mark_handoff(conversation_id)

    return APIResponse(
        success=True,
        data={"status": "handoff_triggered"},
        message="Conversation marked for human handoff",
    )
