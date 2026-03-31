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
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    file: UploadFile = File(...),
) -> APIResponse[CatalogUploadResponse]:
    """Upload CSV untuk product catalog tenant."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
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
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    page: int = 1,
    per_page: int = 20,
) -> PaginatedResponse[ProductResponse]:
    """List products dengan pagination."""
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


@router.get("/search", response_model=APIResponse[list])
async def search_catalog_api(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    q: str = "",
    limit: int = 5,
) -> APIResponse[list]:
    """Semantic search catalog untuk testing dari dashboard."""
    results = await service.search(tenant_id, q, limit)
    return APIResponse(success=True, data=results)


@router.get("/stats", response_model=APIResponse[dict])
async def catalog_stats(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> APIResponse[dict]:
    """Get catalog statistics."""
    _, total = await service.list_products(tenant_id, page=1, per_page=1)
    return APIResponse(success=True, data={"total_products": total})


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
) -> None:
    """Hapus product dari catalog."""
    await service.delete_product(tenant_id, product_id)
