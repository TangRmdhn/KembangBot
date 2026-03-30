"""Lead schemas for Kembang AI."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class LeadCreate(BaseModel):
    """Schema for creating a lead."""

    customer_name: str | None = None
    customer_phone: str
    conversation_id: str | None = None
    estimated_value: float | None = None
    notes: str | None = None


class LeadUpdate(BaseModel):
    """Schema for updating a lead (all fields optional)."""

    customer_name: str | None = None
    status: str | None = None
    estimated_value: float | None = None
    notes: str | None = None


class LeadResponse(BaseModel):
    """Schema for lead response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    customer_name: str | None
    customer_phone: str
    status: str
    estimated_value: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
