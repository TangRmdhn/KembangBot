"""Conversation model for Kembang AI.

Represents a conversation thread between a customer and the AI agent.
"""

from datetime import datetime
from sqlalchemy import String, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class Conversation(Base):
    """Conversation model representing a customer conversation thread.

    Attributes:
        tenant_id: Foreign key to tenant.
        customer_phone: Customer's WhatsApp phone number.
        current_stage: Current stage ID in the conversation flow.
        collected_fields: JSONB field for collected data.
        status: Conversation status (active/completed/handoff/abandoned).
        last_message_at: Timestamp of last message.

    Relationships:
        tenant: The tenant this conversation belongs to.
        messages: List of messages in this conversation.
        lead: Optional lead record associated with this conversation.
    """

    __tablename__ = "conversations"

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    current_stage: Mapped[str] = mapped_column(String(50), default="greeting")
    collected_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    last_message_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )
    lead: Mapped["Lead | None"] = relationship(
        back_populates="conversation",
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_conversations_tenant_phone", "tenant_id", "customer_phone"),
        Index("ix_conversations_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} phone={self.customer_phone} stage={self.current_stage}>"
