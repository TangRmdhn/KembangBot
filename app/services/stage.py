"""Stage configuration service for Kembang AI.

Handles stage config CRUD with Redis caching for flow configs.
"""

import json
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.models.stage_config import StageConfig
from app.schemas.stage import StageConfigCreate, StageConfigUpdate
from app.core.exceptions import StageConfigNotFoundError


class StageService:
    """Service for stage configuration operations.

    Attributes:
        db: Async SQLAlchemy session.
        redis: Async Redis client.
    """

    # Default flow config for tenants without custom stages
    _DEFAULT_CONFIG = {
        "stages": {
            "greeting": {
                "stage_id": "greeting",
                "stage_name": "Salam Pembuka",
                "stage_order": 0,
                "goal": "Menyapa customer dan memulai percakapan",
                "instructions": "Sapa customer dengan ramah, tanyakan apa yang bisa dibantu.",
                "required_fields": [],
                "next_stage": "needs_check",
                "fallback_stage": None,
            },
            "needs_check": {
                "stage_id": "needs_check",
                "stage_name": "Cek Kebutuhan",
                "stage_order": 1,
                "goal": "Mengumpulkan informasi kebutuhan customer",
                "instructions": "Tanyakan detail kebutuhan customer untuk memberikan rekomendasi yang tepat.",
                "required_fields": ["event_type", "date", "location"],
                "next_stage": "booking",
                "fallback_stage": "greeting",
            },
            "booking": {
                "stage_id": "booking",
                "stage_name": "Booking",
                "stage_order": 2,
                "goal": "Menutup penjualan dan melakukan booking",
                "instructions": "Konfirmasi detail dan arahkan customer untuk melakukan booking.",
                "required_fields": ["package_selection"],
                "next_stage": None,
                "fallback_stage": "needs_check",
            },
        },
        "initial_stage": "greeting",
    }

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def get_flow_config(self, tenant_id: str) -> dict:
        """Get compiled flow config for tenant.

        Checks Redis cache first, falls back to DB query.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Flow config dict with stages and initial_stage.
        """
        cache_key = f"kembang:{tenant_id}:stage_config"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            logger.debug("Stage config found in cache", tenant_id=tenant_id)
            return json.loads(cached)

        # Query DB
        result = await self.db.execute(
            select(StageConfig)
            .where(StageConfig.tenant_id == tenant_id)
            .order_by(StageConfig.stage_order)
        )
        stages = result.scalars().all()

        if not stages:
            logger.info("No stage config found, using default", tenant_id=tenant_id)
            return self._DEFAULT_CONFIG.copy()

        # Build flow config
        flow_config = {
            "stages": {},
            "initial_stage": stages[0].stage_id if stages else "greeting",
        }

        for stage in stages:
            flow_config["stages"][stage.stage_id] = {
                "stage_id": stage.stage_id,
                "stage_name": stage.stage_name,
                "stage_order": stage.stage_order,
                "goal": stage.goal,
                "instructions": stage.instructions,
                "required_fields": stage.required_fields,
                "next_stage": stage.next_stage,
                "fallback_stage": stage.fallback_stage,
            }

        # Cache for 10 minutes
        await self.redis.setex(cache_key, 600, json.dumps(flow_config))
        logger.info("Stage config cached", tenant_id=tenant_id)

        return flow_config

    async def create_stage(
        self, tenant_id: str, data: StageConfigCreate
    ) -> StageConfig:
        """Create a new stage configuration.

        Args:
            tenant_id: Tenant UUID.
            data: Stage creation data.

        Returns:
            Created stage config.
        """
        stage = StageConfig(
            tenant_id=tenant_id,
            **data.model_dump(),
        )
        self.db.add(stage)
        await self.db.flush()

        # Invalidate cache
        await self._invalidate_cache(tenant_id)

        logger.info(
            "Stage config created",
            tenant_id=tenant_id,
            stage_id=data.stage_id,
        )
        return stage

    async def update_stage(
        self, tenant_id: str, stage_id: str, data: StageConfigUpdate
    ) -> StageConfig:
        """Update stage configuration.

        Args:
            tenant_id: Tenant UUID.
            stage_id: Stage identifier.
            data: Update data.

        Returns:
            Updated stage config.

        Raises:
            StageConfigNotFoundError: If stage doesn't exist.
        """
        result = await self.db.execute(
            select(StageConfig).where(
                StageConfig.tenant_id == tenant_id,
                StageConfig.stage_id == stage_id,
            )
        )
        stage = result.scalar_one_or_none()

        if not stage:
            raise StageConfigNotFoundError(tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stage, field, value)

        await self.db.flush()

        # Invalidate cache
        await self._invalidate_cache(tenant_id)

        logger.info(
            "Stage config updated",
            tenant_id=tenant_id,
            stage_id=stage_id,
        )
        return stage

    async def delete_stage(self, tenant_id: str, stage_id: str) -> None:
        """Delete a stage configuration.

        Args:
            tenant_id: Tenant UUID.
            stage_id: Stage identifier.
        """
        await self.db.execute(
            delete(StageConfig).where(
                StageConfig.tenant_id == tenant_id,
                StageConfig.stage_id == stage_id,
            )
        )

        # Invalidate cache
        await self._invalidate_cache(tenant_id)

        logger.info(
            "Stage config deleted",
            tenant_id=tenant_id,
            stage_id=stage_id,
        )

    async def replace_all_stages(
        self, tenant_id: str, stages: list[StageConfigCreate]
    ) -> list[StageConfig]:
        """Delete all existing stages and create new ones.

        Atomic: runs in a single transaction.

        Args:
            tenant_id: Tenant UUID.
            stages: List of stage configs to create.

        Returns:
            List of created stage configs.
        """
        # Delete all existing stages for tenant
        await self.db.execute(
            delete(StageConfig).where(StageConfig.tenant_id == tenant_id)
        )

        # Create new stages with order from list index
        new_stages = []
        for i, stage_data in enumerate(stages):
            stage = StageConfig(
                tenant_id=tenant_id,
                stage_id=stage_data.stage_id,
                stage_name=stage_data.stage_name,
                stage_order=i,
                goal=stage_data.goal,
                instructions=stage_data.instructions,
                required_fields=stage_data.required_fields,
                next_stage=stage_data.next_stage,
                fallback_stage=stage_data.fallback_stage,
            )
            self.db.add(stage)
            new_stages.append(stage)

        await self.db.flush()
        await self._invalidate_cache(tenant_id)

        logger.info(
            "All stages replaced",
            tenant_id=tenant_id,
            count=len(new_stages),
        )

        return new_stages

    async def list_stages(self, tenant_id: str) -> list[StageConfig]:
        """List all stages for tenant ordered by stage_order.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            List of stage configs.
        """
        result = await self.db.execute(
            select(StageConfig)
            .where(StageConfig.tenant_id == tenant_id)
            .order_by(StageConfig.stage_order)
        )
        return list(result.scalars().all())

    async def reorder_stages(
        self, tenant_id: str, stage_ids: list[str]
    ) -> None:
        """Bulk reorder stages.

        Args:
            tenant_id: Tenant UUID.
            stage_ids: List of stage IDs in new order.
        """
        for order, stage_id in enumerate(stage_ids):
            await self.db.execute(
                update(StageConfig)
                .where(
                    StageConfig.tenant_id == tenant_id,
                    StageConfig.stage_id == stage_id,
                )
                .values(stage_order=order)
            )

        await self.db.flush()
        await self._invalidate_cache(tenant_id)

        logger.info(
            "Stages reordered",
            tenant_id=tenant_id,
            stage_ids=stage_ids,
        )

    async def _invalidate_cache(self, tenant_id: str) -> None:
        """Delete Redis cache for tenant.

        Args:
            tenant_id: Tenant UUID.
        """
        cache_key = f"kembang:{tenant_id}:stage_config"
        await self.redis.delete(cache_key)
        logger.debug("Stage config cache invalidated", tenant_id=tenant_id)
