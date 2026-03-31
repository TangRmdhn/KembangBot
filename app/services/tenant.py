"""Tenant service for Kembang AI.

Handles tenant CRUD operations with Redis caching for session lookups.
"""

import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate, QRSessionRequest
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

    async def create_qr_session(self, data: QRSessionRequest) -> dict:
        """Create a new QR session for tenant onboarding.

        Generates a unique session ID and stores temporary session data
        in Redis for QR code authentication flow.

        Args:
            data: QR session request data.

        Returns:
            Session ID and temporary token for QR polling.
        """
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        temp_token = uuid.uuid4().hex

        # Store temporary session data in Redis (expires in 10 minutes)
        session_data = {
            "business_name": data.business_name,
            "agent_name": data.agent_name,
            "brand_voice": data.brand_voice,
            "business_type": data.business_type,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        session_key = f"kembang:qr_session:{session_id}"
        await self.redis.setex(session_key, 600, json.dumps(session_data))

        # Store token -> session_id mapping for polling
        token_key = f"kembang:qr_token:{temp_token}"
        await self.redis.setex(token_key, 600, session_id)

        logger.info(
            "QR session created",
            session_id=session_id,
            business_name=data.business_name,
        )

        return {
            "session_id": session_id,
            "temp_token": temp_token,
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
        }

    async def get_qr_session_status(self, session_id: str) -> dict | None:
        """Get QR session authentication status.

        Args:
            session_id: WAHA session identifier.

        Returns:
            Session status info or None if not found.
        """
        session_key = f"kembang:qr_session:{session_id}"
        cached = await self.redis.get(session_key)

        if not cached:
            return None

        session_data = json.loads(cached)
        return {
            "session_id": session_id,
            "status": session_data.get("status", "pending"),
            "business_name": session_data.get("business_name"),
            "phone_number": session_data.get("phone_number"),
            "authenticated_at": session_data.get("authenticated_at"),
        }

    async def complete_qr_authentication(
        self, session_id: str, phone_number: str
    ) -> Tenant | None:
        """Complete QR authentication and create tenant.

        Called when WAHA webhook confirms successful QR scan.

        Args:
            session_id: WAHA session identifier.
            phone_number: WhatsApp phone number from WAHA.

        Returns:
            Created Tenant or None if session not found.
        """
        session_key = f"kembang:qr_session:{session_id}"
        cached = await self.redis.get(session_key)

        if not cached:
            logger.warning("QR session not found", session_id=session_id)
            return None

        session_data = json.loads(cached)

        # Create tenant
        tenant_data = TenantCreate(
            business_name=session_data["business_name"],
            waha_session_id=session_id,
            agent_name=session_data.get("agent_name", "AI Assistant"),
            brand_voice=session_data.get("brand_voice"),
            business_type=session_data.get("business_type", "general"),
            phone_number=phone_number,
        )

        tenant = Tenant(**tenant_data.model_dump())
        self.db.add(tenant)
        await self.db.flush()

        # Update session status
        session_data["status"] = "authenticated"
        session_data["phone_number"] = phone_number
        session_data["authenticated_at"] = datetime.utcnow().isoformat()
        await self.redis.setex(session_key, 3600, json.dumps(session_data))

        logger.info(
            "QR authentication completed, tenant created",
            session_id=session_id,
            tenant_id=str(tenant.id),
            phone_number=phone_number,
        )

        return tenant

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
