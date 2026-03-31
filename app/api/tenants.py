"""Tenant API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends
from typing import Annotated

from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.tenant import TenantService
from app.dependencies import get_tenant_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.post("/", response_model=APIResponse[TenantResponse], status_code=201)
async def create_tenant(
    data: TenantCreate,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> APIResponse[TenantResponse]:
    """Create a new tenant.

    This endpoint creates a new business tenant in the system.
    """
    tenant = await tenant_service.create(data)
    return APIResponse(
        success=True,
        data=TenantResponse.model_validate(tenant),
        message="Tenant created successfully",
    )


@router.get("/", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    page: int = 1,
    per_page: int = 20,
) -> PaginatedResponse[TenantResponse]:
    """List all tenants with pagination.

    Returns paginated list of all tenants in the system.
    """
    tenants, total = await tenant_service.list_all(page=page, per_page=per_page)

    return PaginatedResponse(
        success=True,
        data=[TenantResponse.model_validate(t) for t in tenants],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.get("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def get_tenant(
    tenant_id: str,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    current_tenant: str = Depends(get_current_tenant_id),
) -> APIResponse[TenantResponse]:
    """Get a single tenant by ID.

    Returns tenant details for the specified tenant ID.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    return APIResponse(
        success=True,
        data=TenantResponse.model_validate(tenant),
    )


@router.put("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    current_tenant: str = Depends(get_current_tenant_id),
) -> APIResponse[TenantResponse]:
    """Update an existing tenant.

    Partially updates tenant fields. Only provided fields are updated.
    """
    tenant = await tenant_service.update(tenant_id, data)
    return APIResponse(
        success=True,
        data=TenantResponse.model_validate(tenant),
        message="Tenant updated successfully",
    )
