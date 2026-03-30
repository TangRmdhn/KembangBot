"""FastAPI dependency injection wiring for Kembang AI.

Factory functions that instantiate service classes with their
DB/Redis dependencies for use in route handlers.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.db.session import get_db
from app.db.redis import get_redis
from app.services.tenant import TenantService
from app.services.conversation import ConversationService
from app.services.waha import WAHAClient
from app.services.stage import StageService
from app.services.lead import LeadService
from app.services.catalog import CatalogService
from app.config import settings
from app.core.exceptions import AuthenticationError


async def get_tenant_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TenantService:
    """Get tenant service instance.

    Args:
        db: Database session.
        redis: Redis client.

    Returns:
        TenantService instance.
    """
    return TenantService(db=db, redis=redis)


async def get_conversation_service(
    db: AsyncSession = Depends(get_db),
) -> ConversationService:
    """Get conversation service instance.

    Args:
        db: Database session.

    Returns:
        ConversationService instance.
    """
    return ConversationService(db=db)


async def get_stage_service(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> StageService:
    """Get stage service instance.

    Args:
        db: Database session.
        redis: Redis client.

    Returns:
        StageService instance.
    """
    return StageService(db=db, redis=redis)


async def get_lead_service(
    db: AsyncSession = Depends(get_db),
) -> LeadService:
    """Get lead service instance.

    Args:
        db: Database session.

    Returns:
        LeadService instance.
    """
    return LeadService(db=db)


async def get_catalog_service(
    db: AsyncSession = Depends(get_db),
) -> CatalogService:
    """Get catalog service instance.

    Args:
        db: Database session.

    Returns:
        CatalogService instance.
    """
    return CatalogService(db=db)


# WAHAClient is a singleton (reuses httpx.AsyncClient)
_waha_client: WAHAClient | None = None


async def get_waha_client() -> WAHAClient:
    """Get WAHA client instance (singleton).

    Returns:
        WAHAClient instance.
    """
    global _waha_client
    if _waha_client is None:
        _waha_client = WAHAClient()
    return _waha_client


async def cleanup_waha_client() -> None:
    """Close WAHA client. Call on app shutdown."""
    global _waha_client
    if _waha_client:
        await _waha_client.close()
        _waha_client = None


async def get_current_tenant_id(
    authorization: str = Header(...),
) -> str:
    """Extract and verify tenant ID from Authorization header.

    MVP: expects 'Bearer {APP_SECRET_KEY}:{tenant_id}' format.

    Args:
        authorization: Authorization header value.

    Returns:
        Tenant ID extracted from token.

    Raises:
        AuthenticationError: If token is invalid or missing.

    Todo:
        Replace with proper JWT that encodes tenant_id.
    """
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = authorization[7:]  # Remove "Bearer " prefix

    # Try parsing "key:tenant_id" format
    if ":" in token:
        key, tenant_id = token.split(":", 1)
        if key == settings.APP_SECRET_KEY:
            return tenant_id
    elif token == settings.APP_SECRET_KEY:
        # For MVP, return a placeholder
        return "mvp-tenant-id"

    raise AuthenticationError("Invalid API key")
