"""Lead management API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.lead import LeadService
from app.dependencies import get_lead_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("/", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    status: str | None = None,
    page: int = 1,
    per_page: int = 20,
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> PaginatedResponse[LeadResponse]:
    """List leads for tenant with filtering.

    Returns paginated list of leads, optionally filtered by status.
    """
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
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[dict]:
    """Get lead counts by status.

    Returns statistics about leads grouped by status.
    """
    stats = await lead_service.get_stats(tenant_id)
    return APIResponse(
        success=True,
        data=stats,
    )


@router.get("/{lead_id}", response_model=APIResponse[LeadResponse])
async def get_lead(
    lead_id: str,
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[LeadResponse]:
    """Get a single lead by ID.

    Returns lead details for the specified lead ID.
    """
    lead = await lead_service.get_by_id(tenant_id, lead_id)
    return APIResponse(
        success=True,
        data=LeadResponse.model_validate(lead),
    )


@router.put("/{lead_id}", response_model=APIResponse[LeadResponse])
async def update_lead(
    lead_id: str,
    data: LeadUpdate,
    lead_service: Annotated[LeadService, Depends(get_lead_service)],
    tenant_id: str = Depends(get_current_tenant_id),
) -> APIResponse[LeadResponse]:
    """Update an existing lead.

    Partially updates lead fields. Status transitions are validated.
    """
    lead = await lead_service.update(tenant_id, lead_id, data)
    return APIResponse(
        success=True,
        data=LeadResponse.model_validate(lead),
        message="Lead updated successfully",
    )
