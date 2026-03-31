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
    stage_ids: list[str]


class FlowValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class ApplyTemplateRequest(BaseModel):
    template_id: str
    agent_name: str = "Asisten Virtual"
    business_name: str
    brand_voice: str = "ramah dan profesional"


@router.get("/", response_model=APIResponse[list[StageConfigResponse]])
async def list_stages(
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[list[StageConfigResponse]]:
    """List semua stages untuk tenant, ordered by stage_order."""
    stages = await stage_service.list_stages(tenant_id)
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in stages],
    )


@router.post("/", response_model=APIResponse[StageConfigResponse], status_code=201)
async def create_stage(
    data: StageConfigCreate,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[StageConfigResponse]:
    """Buat stage baru."""
    stage = await stage_service.create_stage(tenant_id, data)
    return APIResponse(
        success=True,
        data=StageConfigResponse.model_validate(stage),
        message="Stage created successfully",
    )


@router.put("/flow", response_model=APIResponse[list[StageConfigResponse]])
async def save_full_flow(
    stages: list[StageConfigCreate],
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[list[StageConfigResponse]]:
    """Replace seluruh stage flow sekaligus."""
    result = await stage_service.replace_all_stages(tenant_id, stages)
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in result],
        message="Flow saved successfully",
    )


@router.get("/flow-config", response_model=APIResponse[FlowConfigResponse])
async def get_flow_config(
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[FlowConfigResponse]:
    """Get compiled flow config untuk LangGraph engine."""
    config = await stage_service.get_flow_config(tenant_id)
    return APIResponse(
        success=True,
        data=FlowConfigResponse.model_validate(config),
    )


@router.get("/templates", response_model=APIResponse[list])
async def list_templates(
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[list]:
    """List template flow yang tersedia."""
    from app.services.template import TemplateService
    from app.db.redis import get_redis
    redis = await get_redis()
    service = TemplateService(db=None, redis=redis)
    return APIResponse(success=True, data=service.list_templates())


@router.post("/apply-template", response_model=APIResponse[list[StageConfigResponse]])
async def apply_template(
    body: ApplyTemplateRequest,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[list[StageConfigResponse]]:
    """Apply template flow ke tenant. Menggantikan semua stage yang ada."""
    from app.services.template import TemplateService
    from app.db.redis import get_redis
    redis = await get_redis()
    template_service = TemplateService(db=stage_service.db, redis=redis)
    try:
        stages = await template_service.apply_template(
            tenant_id=tenant_id,
            template_id=body.template_id,
            agent_name=body.agent_name,
            business_name=body.business_name,
            brand_voice=body.brand_voice,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in stages],
        message=f"Template '{body.template_id}' berhasil diterapkan",
    )


@router.post("/reorder", response_model=APIResponse[list[StageConfigResponse]])
async def reorder_stages(
    body: ReorderRequest,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[list[StageConfigResponse]]:
    """Reorder stages dengan mengirim stage_ids dalam urutan yang diinginkan."""
    await stage_service.reorder_stages(tenant_id, body.stage_ids)
    stages = await stage_service.list_stages(tenant_id)
    return APIResponse(
        success=True,
        data=[StageConfigResponse.model_validate(s) for s in stages],
        message="Stages reordered successfully",
    )


@router.put("/{stage_id}", response_model=APIResponse[StageConfigResponse])
async def update_stage(
    stage_id: str,
    data: StageConfigUpdate,
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[StageConfigResponse]:
    """Update stage configuration."""
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
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> None:
    """Hapus stage configuration."""
    await stage_service.delete_stage(tenant_id, stage_id)


@router.post("/validate", response_model=FlowValidationResponse)
async def validate_flow(
    stages: list[StageConfigCreate],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> FlowValidationResponse:
    """Validasi flow config tanpa menyimpannya."""
    errors = []
    warnings = []
    stage_ids = [s.stage_id for s in stages]

    if not stages:
        errors.append("Flow must have at least one stage")
    if len(stage_ids) != len(set(stage_ids)):
        errors.append("Duplicate stage_id found")

    for stage in stages:
        if stage.next_stage and stage.next_stage not in stage_ids:
            errors.append(
                f"Stage '{stage.stage_id}' references unknown next_stage '{stage.next_stage}'"
            )
        if stage.fallback_stage and stage.fallback_stage not in stage_ids:
            warnings.append(
                f"Stage '{stage.stage_id}' references unknown fallback_stage '{stage.fallback_stage}'"
            )

    if stages and stages[0].required_fields:
        warnings.append(
            "First stage has required_fields — consider removing them for a natural greeting"
        )

    return FlowValidationResponse(valid=len(errors) == 0, errors=errors, warnings=warnings)
