"""Message model for Kembang AI.

Represents a single message within a conversation.
"""

from sqlalchemy import String, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Message(Base):
    """Message model representing a single message in a conversation.

    Attributes:
        conversation_id: Foreign key to conversation.
        role: Message role ("human" or "ai").
        content: Message text content.
        waha_message_id: Original WAHA message ID if from WhatsApp.

    Relationships:
        conversation: The conversation this message belongs to.
    """

    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    waha_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} conversation={self.conversation_id}>"
