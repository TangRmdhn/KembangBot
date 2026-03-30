"""Lead model for Kembang AI.

Represents a sales lead generated from conversations.
"""

from decimal import Decimal
from sqlalchemy import String, ForeignKey, Index, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class Lead(Base):
    """Lead model representing a sales lead.

    Attributes:
        tenant_id: Foreign key to tenant.
        conversation_id: Optional foreign key to conversation.
        customer_name: Customer's name.
        customer_phone: Customer's phone number.
        status: Lead status (new/contacted/negotiating/closed_won/closed_lost).
        estimated_value: Estimated deal value in IDR.
        notes: Additional notes about the lead.
        metadata_: Extra metadata in JSON format.

    Relationships:
        tenant: The tenant this lead belongs to.
        conversation: Optional conversation that generated this lead.
    """

    __tablename__ = "leads"

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id"),
        nullable=True,
    )
    customer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new")
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="leads")
    conversation: Mapped["Conversation | None"] = relationship(back_populates="lead")

    def __repr__(self) -> str:
        return f"<Lead id={self.id} customer={self.customer_name} status={self.status}>"
