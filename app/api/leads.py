"""Lead management API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends
from typing import Annotated

from app.schemas.lead import LeadUpdate, LeadResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.lead import LeadService
from app.dependencies import get_lead_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("/", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> PaginatedResponse[LeadResponse]:
    """List leads untuk tenant dengan filtering."""
    leads, total = await lead_service.list_by_tenant(
        tenant_id=tenant_id,
        status=status,
        page=page,
        per_page=per_page,
    )
    return PaginatedResponse(
        success=True,
        data=[LeadResponse.model_validate(l) for l in leads],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.get("/stats", response_model=APIResponse[dict])
async def get_lead_stats(
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[dict]:
    """Get lead counts by status."""
    stats = await lead_service.get_stats(tenant_id)
    return APIResponse(success=True, data=stats)


@router.get("/{lead_id}", response_model=APIResponse[LeadResponse])
async def get_lead(
    lead_id: str,
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[LeadResponse]:
    """Get single lead by ID."""
    lead = await lead_service.get_by_id(tenant_id, lead_id)
    return APIResponse(success=True, data=LeadResponse.model_validate(lead))


@router.put("/{lead_id}", response_model=APIResponse[LeadResponse])
async def update_lead(
    lead_id: str,
    data: LeadUpdate,
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[LeadResponse]:
    """Update lead. Status transitions divalidasi."""
    lead = await lead_service.update(tenant_id, lead_id, data)
    return APIResponse(
        success=True,
        data=LeadResponse.model_validate(lead),
        message="Lead updated successfully",
    )
