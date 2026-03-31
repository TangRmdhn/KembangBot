"""Tenant model for Kembang AI.

Represents a business tenant (customer) using the platform.
"""

from sqlalchemy import String, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Tenant(Base):
    """Tenant model representing a business customer.

    Attributes:
        business_name: Name of the business.
        waha_session_id: WAHA session identifier (unique).
        agent_name: Name the AI introduces itself as.
        brand_voice: Tone instructions for the AI.
        business_type: Type of business (product/service/general).
        phone_number: WhatsApp phone number.
        subscription_plan: Subscription tier.
        is_active: Whether the tenant is active.

    Relationships:
        conversations: List of conversations for this tenant.
        stage_configs: List of stage configurations.
        leads: List of leads for this tenant.
        products: List of products in the catalog.
    """

    __tablename__ = "tenants"

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    waha_session_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(50), default="AI Assistant")
    brand_voice: Mapped[str | None] = mapped_column(String(500), nullable=True)
    business_type: Mapped[str] = mapped_column(String(50), default="general")
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="basic")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    stage_configs: Mapped[list["StageConfig"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        order_by="StageConfig.stage_order",
    )
    leads: Mapped[list["Lead"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["Product"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["TenantDocument"]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.business_name}>"
