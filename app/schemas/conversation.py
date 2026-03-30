"""Conversation schemas for Kembang AI."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    """Schema for message response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    customer_phone: str
    current_stage: str
    collected_fields: dict
    status: str
    last_message_at: datetime | None
    created_at: datetime


class ConversationDetail(ConversationResponse):
    """Schema for conversation with messages."""

    messages: list[MessageResponse]
