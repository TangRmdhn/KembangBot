"""Tenant service for Kembang AI.

Handles tenant CRUD operations with Redis caching for session lookups.
"""

import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.core.exceptions import TenantNotFoundError


class TenantService:
    """Service for tenant operations.

    Attributes:
        db: Async SQLAlchemy session.
        redis: Async Redis client.
    """

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def get_by_session(self, session_id: str) -> Tenant | None:
        """Lookup tenant by WAHA session ID.

        Checks Redis cache first, falls back to DB query, caches result for 5 min.

        Args:
            session_id: WAHA session identifier.

        Returns:
            Tenant if found, None otherwise.
        """
        cache_key = f"kembang:session_map:{session_id}"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            tenant_data = json.loads(cached)
            logger.debug("Tenant found in cache", session_id=session_id)
            return Tenant(**tenant_data)

        # Fallback to DB
        result = await self.db.execute(
            select(Tenant).where(Tenant.waha_session_id == session_id)
        )
        tenant = result.scalar_one_or_none()

        if tenant:
            # Cache for 5 minutes
            tenant_dict = {
                "id": str(tenant.id),
                "business_name": tenant.business_name,
                "waha_session_id": tenant.waha_session_id,
                "agent_name": tenant.agent_name,
                "brand_voice": tenant.brand_voice,
                "business_type": tenant.business_type,
                "phone_number": tenant.phone_number,
                "subscription_plan": tenant.subscription_plan,
                "is_active": tenant.is_active,
            }
            await self.redis.setex(cache_key, 300, json.dumps(tenant_dict))
            logger.info("Tenant cached", session_id=session_id, tenant_id=str(tenant.id))

        return tenant

    async def get_by_id(self, tenant_id: str) -> Tenant:
        """Get tenant by UUID.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Tenant instance.

        Raises:
            TenantNotFoundError: If tenant doesn't exist.
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise TenantNotFoundError(tenant_id)

        return tenant

    async def create(self, data: TenantCreate) -> Tenant:
        """Create a new tenant.

        Args:
            data: Tenant creation data.

        Returns:
            Created tenant instance.
        """
        tenant = Tenant(**data.model_dump())
        self.db.add(tenant)
        await self.db.flush()

        # Invalidate session map cache
        await self.redis.delete(f"kembang:session_map:{data.waha_session_id}")

        logger.info("Tenant created", tenant_id=str(tenant.id))
        return tenant

    async def update(self, tenant_id: str, data: TenantUpdate) -> Tenant:
        """Update tenant partially.

        Args:
            tenant_id: Tenant UUID.
            data: Update data.

        Returns:
            Updated tenant instance.

        Raises:
            TenantNotFoundError: If tenant doesn't exist.
        """
        tenant = await self.get_by_id(tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.flush()

        # Invalidate cache
        await self.redis.delete(f"kembang:session_map:{tenant.waha_session_id}")

        logger.info("Tenant updated", tenant_id=tenant_id)
        return tenant

    async def list_all(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination.

        Args:
            page: Page number (1-indexed).
            per_page: Items per page.

        Returns:
            Tuple of (tenants list, total count).
        """
        offset = (page - 1) * per_page

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Tenant)
        )
        total = count_result.scalar()

        # Get paginated results
        result = await self.db.execute(
            select(Tenant).offset(offset).limit(per_page)
        )
        tenants = result.scalars().all()

        return list(tenants), total
