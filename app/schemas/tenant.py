"""Tenant schemas for Kembang AI."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TenantCreate(BaseModel):
    """Schema for creating a tenant."""

    business_name: str
    waha_session_id: str
    agent_name: str = "AI Assistant"
    brand_voice: str | None = None
    business_type: str = "general"
    phone_number: str | None = None


class TenantUpdate(BaseModel):
    """Schema for updating a tenant (all fields optional)."""

    business_name: str | None = None
    agent_name: str | None = None
    brand_voice: str | None = None
    business_type: str | None = None
    is_active: bool | None = None


class TenantResponse(BaseModel):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    business_name: str
    waha_session_id: str
    agent_name: str
    brand_voice: str | None
    business_type: str
    phone_number: str | None
    subscription_plan: str
    is_active: bool
    created_at: datetime
