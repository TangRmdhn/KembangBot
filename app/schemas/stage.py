"""Stage configuration schemas for Kembang AI."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class StageConfigCreate(BaseModel):
    """Schema for creating a stage configuration."""

    stage_id: str
    stage_name: str
    stage_order: int
    goal: str
    instructions: str
    required_fields: list[str] = []
    next_stage: str | None = None
    fallback_stage: str = "greeting"

    @field_validator("stage_id")
    @classmethod
    def validate_stage_id(cls, v: str) -> str:
        """Validate stage_id is alphanumeric with underscores."""
        if not v.replace("_", "").isalnum():
            raise ValueError("stage_id must be alphanumeric with underscores")
        return v


class StageConfigUpdate(BaseModel):
    """Schema for updating a stage configuration (all fields optional)."""

    stage_name: str | None = None
    stage_order: int | None = None
    goal: str | None = None
    instructions: str | None = None
    required_fields: list[str] | None = None
    next_stage: str | None = None
    fallback_stage: str | None = None


class StageConfigResponse(BaseModel):
    """Schema for stage configuration response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    stage_id: str
    stage_name: str
    stage_order: int
    goal: str
    instructions: str
    required_fields: list[str]
    next_stage: str | None
    fallback_stage: str
    created_at: datetime


class FlowConfigResponse(BaseModel):
    """Full flow configuration for a tenant — used by LangGraph."""

    stages: dict[str, StageConfigResponse]
    initial_stage: str
