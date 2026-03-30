"""Seeder service for Kembang AI demo data.

Creates demo tenants with stage configs and sample products
for showcasing the platform to pilot clients.
"""

import csv
import io
import json
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from loguru import logger

from app.models.tenant import Tenant
from app.models.stage_config import StageConfig
from app.models.product import Product


class SeederService:
    """Service for seeding demo data.

    Attributes:
        db: Async SQLAlchemy session.
        redis: Async Redis client.
    """

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.seeds_dir = Path(__file__).parent.parent / "seeds"

    async def seed_demo_data(self) -> dict:
        """Seed demo tenants with stage configs and products.

        Returns:
            Summary dict with counts of created entities.

        Idempotent: skips if demo tenants already exist.
        """
        summary = {
            "tenants_created": 0,
            "stages_created": 0,
            "products_created": 0,
        }

        # Seed photography demo
        photo_result = await self._seed_tenant(
            flow_file="photography_flow.json",
            products_file="photography_products.csv",
        )
        summary["tenants_created"] += photo_result["tenant_created"]
        summary["stages_created"] += photo_result["stages_created"]
        summary["products_created"] += photo_result["products_created"]

        # Seed sneaker shop demo
        sneaker_result = await self._seed_tenant(
            flow_file="sneaker_shop_flow.json",
            products_file="sneaker_products.csv",
        )
        summary["tenants_created"] += sneaker_result["tenant_created"]
        summary["stages_created"] += sneaker_result["stages_created"]
        summary["products_created"] += sneaker_result["products_created"]

        logger.info("Demo data seeded", summary=summary)
        return summary

    async def _seed_tenant(
        self,
        flow_file: str,
        products_file: str,
    ) -> dict:
        """Seed a single tenant from JSON flow and CSV products.

        Args:
            flow_file: JSON filename in seeds directory.
            products_file: CSV filename in seeds directory.

        Returns:
            Dict with counts of created entities.
        """
        result = {
            "tenant_created": 0,
            "stages_created": 0,
            "products_created": 0,
        }

        # Load flow config
        flow_path = self.seeds_dir / flow_file
        with open(flow_path, "r", encoding="utf-8") as f:
            flow_data = json.load(f)

        tenant_data = flow_data["tenant"]
        stages_data = flow_data["stages"]

        # Check if tenant already exists
        existing = await self.db.execute(
            select(Tenant).where(
                Tenant.waha_session_id == tenant_data["waha_session_id"]
            )
        )
        if existing.scalar_one_or_none():
            logger.info(
                "Tenant already exists, skipping",
                session_id=tenant_data["waha_session_id"],
            )
            return result

        # Create tenant
        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        await self.db.flush()
        result["tenant_created"] = 1

        logger.info(
            "Demo tenant created",
            tenant_id=str(tenant.id),
            business_name=tenant.business_name,
        )

        # Create stages
        for stage_dict in stages_data:
            stage = StageConfig(
                tenant_id=tenant.id,
                **stage_dict,
            )
            self.db.add(stage)
            result["stages_created"] += 1

        await self.db.flush()

        # Load and create products
        products_path = self.seeds_dir / products_file
        with open(products_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                product = Product(
                    tenant_id=tenant.id,
                    name=row["name"],
                    description=row.get("description"),
                    price=float(row["price"]) if row.get("price") else None,
                    category=row.get("category"),
                )
                self.db.add(product)
                result["products_created"] += 1

        await self.db.flush()

        logger.info(
            "Demo tenant seeded",
            tenant_id=str(tenant.id),
            stages=result["stages_created"],
            products=result["products_created"],
        )

        return result


async def main():
    """Run seeder directly for CLI usage."""
    import asyncio
    from app.db.session import async_session_factory
    from app.db.redis import redis_client, init_redis

    async def run_seed():
        # Init Redis
        await init_redis()

        async with async_session_factory() as db:
            seeder = SeederService(db=db, redis=redis_client)
            result = await seeder.seed_demo_data()
            print(f"Seeding complete: {result}")

    asyncio.run(run_seed())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
