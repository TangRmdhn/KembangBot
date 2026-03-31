"""Internal API endpoints — only for inter-service communication.

All endpoints here use INTERNAL_API_KEY for auth,
not regular user JWT. Not accessible by frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.db.session import get_db

router = APIRouter(prefix="/internal", tags=["internal"])


async def verify_internal_key(authorization: str = Header(...)) -> None:
    """Verify internal API key for service-to-service communication."""
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing Authorization header")
    token = authorization[7:]
    if token != settings.INTERNAL_API_KEY:
        raise AuthenticationError("Invalid internal API key")


# ── Schema ──

class EmbedProductsRequest(BaseModel):
    """Request body for triggering catalog embedding."""
    tenant_id: str
    products: list[dict]  # list of products from Backend Service


class EmbedProductsResponse(BaseModel):
    """Response after embedding completes."""
    success: bool
    embedded_count: int
    errors: list[str] = []


# ── Endpoints ──

@router.post(
    "/catalog/embed",
    response_model=EmbedProductsResponse,
    dependencies=[Depends(verify_internal_key)],
)
async def trigger_catalog_embed(
    body: EmbedProductsRequest,
) -> EmbedProductsResponse:
    """Trigger embedding for tenant product catalog.

    Called by Backend Service (Arsya) after tenant uploads CSV.
    AI Service will:
    1. Delete old tenant embeddings
    2. Generate new embeddings from products
    3. Save to pgvector collection catalog_{tenant_id}

    Auth: INTERNAL_API_KEY (shared secret between services)
    """
    from app.services.embedding import EmbeddingService

    logger.info(
        "Internal catalog embed triggered",
        tenant_id=body.tenant_id,
        product_count=len(body.products),
    )

    if not body.products:
        raise HTTPException(400, "products cannot be empty")

    service = EmbeddingService()
    errors = []
    embedded_count = 0

    try:
        # Delete old embeddings
        await service.delete_tenant_embeddings(body.tenant_id)

        # Generate new embeddings
        embedded_count = await service.embed_products(
            tenant_id=body.tenant_id,
            products=body.products,
        )

    except Exception as e:
        error_msg = str(e)
        errors.append(error_msg)
        logger.error(
            "Catalog embed failed",
            tenant_id=body.tenant_id,
            error=error_msg,
        )
        raise HTTPException(500, f"Embedding failed: {error_msg}")

    logger.info(
        "Catalog embed completed",
        tenant_id=body.tenant_id,
        embedded_count=embedded_count,
    )

    return EmbedProductsResponse(
        success=True,
        embedded_count=embedded_count,
        errors=errors,
    )


@router.delete(
    "/catalog/embed/{tenant_id}",
    dependencies=[Depends(verify_internal_key)],
)
async def delete_catalog_embeddings(tenant_id: str) -> dict:
    """Delete all catalog embeddings for tenant.

    Called by Backend Service before re-upload catalog,
    or when tenant is deleted.
    """
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    await service.delete_tenant_embeddings(tenant_id)

    logger.info("Catalog embeddings deleted", tenant_id=tenant_id)
    return {"success": True, "tenant_id": tenant_id}


@router.get(
    "/tenants/{tenant_id}/conversations",
    dependencies=[Depends(verify_internal_key)],
)
async def list_conversations_internal(
    tenant_id: str,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List conversations for tenant — for Backend Service dashboard.

    Optional: Backend Service can query DB directly or use this endpoint.
    """
    from app.services.conversation import ConversationService

    service = ConversationService(db=db)
    conversations, total = await service.list_by_tenant(
        tenant_id=tenant_id,
        page=page,
        per_page=per_page,
    )

    return {
        "success": True,
        "data": [
            {
                "id": str(c.id),
                "customer_phone": c.customer_phone,
                "current_stage": c.current_stage,
                "status": c.status,
                "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
                "created_at": c.created_at.isoformat(),
            }
            for c in conversations
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }
