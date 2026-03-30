"""Product model for Kembang AI.

Represents a product in the tenant's catalog.
"""

from decimal import Decimal
from sqlalchemy import String, ForeignKey, Index, Text, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class Product(Base):
    """Product model representing a catalog item.

    Attributes:
        tenant_id: Foreign key to tenant.
        name: Product name.
        description: Product description.
        price: Product price in IDR.
        category: Product category.
        metadata_: Extra metadata from CSV upload.
        is_active: Whether the product is active.

    Relationships:
        tenant: The tenant this product belongs to.
    """

    __tablename__ = "products"

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="products")

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} tenant={self.tenant_id}>"
