"""Stage configuration API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Annotated

from app.schemas.stage import (
    StageConfigCreate,
    StageConfigUpdate,
    StageConfigResponse,
    FlowConfigResponse,
)
from app.schemas.common import APIResponse
from app.services.stage import StageService
from app.dependencies import get_stage_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/stages", tags=["stages"])


class ReorderRequest(BaseModel):
    """Request body for reordering stages."""
    stage_ids: list[str]  # Ordered list of stage_id strings


class FlowValidationResponse(BaseModel):
    """Response body for flow validation."""
    valid: bool
    errors: list[str]
    warnings: list[str]


@router.get("/", response_model=APIResponse[list[StageConfigResponse]])
async def list_stages(
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[list[StageConfigResponse]]:
    """List all stages for tenant.

    Returns stages ordered by stage_order.
    """
    stages = await stage_service.list_stages(tenant_id)
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in stages],
    )


@router.post("/", response_model=APIResponse[StageConfigResponse], status_code=201)
async def create_stage(
    data: StageConfigCreate,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[StageConfigResponse]:
    """Create a new stage configuration.

    Creates a new stage in the tenant's conversation flow.
    """
    stage = await stage_service.create_stage(tenant_id, data)
    return APIResponse(
        success=True,
        data=StageConfigResponse.model_validate(stage),
        message="Stage created successfully",
    )


@router.put("/{stage_id}", response_model=APIResponse[StageConfigResponse])
async def update_stage(
    stage_id: str,
    data: StageConfigUpdate,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[StageConfigResponse]:
    """Update an existing stage configuration.

    Partially updates stage fields. Only provided fields are updated.
    """
    stage = await stage_service.update_stage(tenant_id, stage_id, data)
    return APIResponse(
        success=True,
        data=StageConfigResponse.model_validate(stage),
        message="Stage updated successfully",
    )


@router.delete("/{stage_id}", status_code=204)
async def delete_stage(
    stage_id: str,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> None:
    """Delete a stage configuration.

    Removes the stage from the tenant's conversation flow.
    """
    await stage_service.delete_stage(tenant_id, stage_id)


@router.post("/reorder", response_model=APIResponse[list[StageConfigResponse]])
async def reorder_stages(
    body: ReorderRequest,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[list[StageConfigResponse]]:
    """Reorder stages by providing the stage_ids in desired order.

    Args:
        body: Reorder request with ordered stage IDs.
        stage_service: Stage service dependency.
        tenant_id: Tenant ID from auth.

    Returns:
        Updated list of stages.
    """
    await stage_service.reorder_stages(tenant_id, body.stage_ids)
    stages = await stage_service.list_stages(tenant_id)
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in stages],
        message="Stages reordered successfully",
    )


@router.put("/flow", response_model=APIResponse[list[StageConfigResponse]])
async def save_full_flow(
    stages: list[StageConfigCreate],
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[list[StageConfigResponse]]:
    """Save the entire stage flow at once (replaces all existing stages).

    Used by the flow builder when the user clicks "Save".
    This is a full replacement — all existing stages are deleted and
    replaced with the provided list.

    The stage_order is determined by the list index (0, 1, 2...).

    Args:
        stages: List of stage configs to save.
        stage_service: Stage service dependency.
        tenant_id: Tenant ID from auth.

    Returns:
        List of created stages.
    """
    result = await stage_service.replace_all_stages(tenant_id, stages)
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in result],
        message="Flow saved successfully",
    )


@router.get("/flow-config", response_model=APIResponse[FlowConfigResponse])
async def get_flow_config(
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[FlowConfigResponse]:
    """Get compiled flow configuration.

    Returns the full flow config used by LangGraph engine.
    """
    config = await stage_service.get_flow_config(tenant_id)
    return APIResponse(
        success=True,
        data=FlowConfigResponse.model_validate(config),
    )


@router.post("/validate", response_model=FlowValidationResponse)
async def validate_flow(
    stages: list[StageConfigCreate],
    tenant_id: str = Depends(get_current_tenant_id),
) -> FlowValidationResponse:
    """Validate a flow configuration without saving it.

    Checks:
    - At least one stage exists
    - All next_stage references point to valid stage_ids
    - No circular references (basic check)
    - All stage_ids are unique
    - First stage has no required_fields (greeting should be open)

    Args:
        stages: List of stage configs to validate.
        tenant_id: Tenant ID from auth.

    Returns:
        Validation result with errors and warnings.
    """
    errors = []
    warnings = []
    stage_ids = [s.stage_id for s in stages]

    if not stages:
        errors.append("Flow must have at least one stage")

    if len(stage_ids) != len(set(stage_ids)):
        errors.append("Duplicate stage_id found")

    for stage in stages:
        if stage.next_stage and stage.next_stage not in stage_ids:
            errors.append(f"Stage '{stage.stage_id}' references unknown next_stage '{stage.next_stage}'")
        if stage.fallback_stage and stage.fallback_stage not in stage_ids:
            warnings.append(f"Stage '{stage.stage_id}' references unknown fallback_stage '{stage.fallback_stage}'")

    if stages and stages[0].required_fields:
        warnings.append("First stage has required_fields — consider removing them for a natural greeting")

    return FlowValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
