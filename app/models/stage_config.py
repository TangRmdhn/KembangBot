"""StageConfig model for Kembang AI.

Represents a stage configuration in the conversation flow.
"""

from sqlalchemy import String, ForeignKey, Index, Integer, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class StageConfig(Base):
    """Stage configuration model for conversation flow.

    Attributes:
        tenant_id: Foreign key to tenant.
        stage_id: Unique stage identifier per tenant (e.g., "greeting").
        stage_name: Display name for the stage.
        stage_order: Order in the flow sequence.
        goal: Short description of stage goal.
        instructions: Full system prompt instructions.
        required_fields: List of field names to collect.
        next_stage: Next stage ID to transition to.
        fallback_stage: Fallback stage for out-of-scope inputs.

    Relationships:
        tenant: The tenant this stage config belongs to.
    """

    __tablename__ = "stage_configs"

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    stage_id: Mapped[str] = mapped_column(String(50), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    required_fields: Mapped[list[str]] = mapped_column(JSONB, default=list)
    next_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_stage: Mapped[str] = mapped_column(String(50), default="greeting")

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="stage_configs")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("tenant_id", "stage_id", name="uq_tenant_stage"),
        Index("ix_stage_configs_tenant_order", "tenant_id", "stage_order"),
    )

    def __repr__(self) -> str:
        return f"<StageConfig id={self.id} stage={self.stage_id} tenant={self.tenant_id}>"
