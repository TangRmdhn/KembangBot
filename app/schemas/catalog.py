"""Catalog schemas for Kembang AI."""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class CatalogUploadResponse(BaseModel):
    """Schema for catalog upload response."""

    total_products: int
    embedded_count: int
    errors: list[str]


class ProductResponse(BaseModel):
    """Schema for product response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    price: float | None
    category: str | None
    is_active: bool
