"""Catalog management API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import Annotated

from app.schemas.catalog import CatalogUploadResponse, ProductResponse
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.catalog import CatalogService
from app.dependencies import get_catalog_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.post("/upload", response_model=APIResponse[CatalogUploadResponse])
async def upload_catalog(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
    service: Annotated[CatalogService, Depends(get_catalog_service)] = None,
) -> APIResponse[CatalogUploadResponse]:
    """Upload a CSV file to populate the product/service catalog.

    The CSV should have at minimum a 'name' column. Optional columns:
    description, price, category. Extra columns are stored as metadata.

    This replaces the entire catalog for the tenant (full re-upload).

    Args:
        file: CSV file to upload.
        tenant_id: Tenant ID from auth.
        service: Catalog service dependency.

    Returns:
        Upload result with product counts and any errors.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    # Validate file size (max 5MB for MVP)
    MAX_SIZE = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    result = await service.upload_csv(
        tenant_id=tenant_id,
        file_content=content,
        filename=file.filename,
    )

    return APIResponse(
        success=True,
        data=CatalogUploadResponse(**result),
        message=f"Uploaded {result['total_products']} products",
    )


@router.get("/products", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = 1,
    per_page: int = 20,
    tenant_id: str = Depends(get_current_tenant_id),
    service: Annotated[CatalogService, Depends(get_catalog_service)] = None,
) -> PaginatedResponse[ProductResponse]:
    """List products for tenant with pagination.

    Returns paginated list of all products in the catalog.

    Args:
        page: Page number.
        per_page: Items per page.
        tenant_id: Tenant ID from auth.
        service: Catalog service dependency.

    Returns:
        Paginated product list.
    """
    products, total = await service.list_products(
        tenant_id=tenant_id,
        page=page,
        per_page=per_page,
    )

    return PaginatedResponse(
        success=True,
        data=[ProductResponse.model_validate(p) for p in products],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.get("/search")
async def search_catalog_api(
    q: str,
    limit: int = 5,
    tenant_id: str = Depends(get_current_tenant_id),
    service: Annotated[CatalogService, Depends(get_catalog_service)] = None,
) -> APIResponse[list]:
    """Search the catalog using semantic similarity.

    This endpoint is for the dashboard to test search.
    The AI agent uses the same search via LangGraph tools.

    Args:
        q: Search query.
        limit: Max results.
        tenant_id: Tenant ID from auth.
        service: Catalog service dependency.

    Returns:
        Search results with relevance scores.
    """
    results = await service.search(tenant_id, q, limit)
    return APIResponse(
        success=True,
        data=results,
    )


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    service: Annotated[CatalogService, Depends(get_catalog_service)] = None,
) -> None:
    """Delete a product from catalog.

    Removes the product from the tenant's catalog.

    Args:
        product_id: Product UUID.
        tenant_id: Tenant ID from auth.
        service: Catalog service dependency.
    """
    await service.delete_product(tenant_id, product_id)


@router.get("/stats", response_model=APIResponse[dict])
async def catalog_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    service: Annotated[CatalogService, Depends(get_catalog_service)] = None,
) -> APIResponse[dict]:
    """Get catalog statistics for the dashboard.

    Args:
        tenant_id: Tenant ID from auth.
        service: Catalog service dependency.

    Returns:
        Catalog statistics.
    """
    _, total = await service.list_products(tenant_id, page=1, per_page=1)
    return APIResponse(
        success=True,
        data={"total_products": total},
    )
