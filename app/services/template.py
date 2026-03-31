"""Template flow service for Kembang AI.

Provides ready-to-use conversation flow templates for tenants
who don't want to setup flows from scratch.
"""

import json
from pathlib import Path
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.services.stage import StageService
from app.schemas.stage import StageConfigCreate


# Seeds folder location
SEEDS_DIR = Path(__file__).parent.parent / "seeds"

# Registry of available templates
AVAILABLE_TEMPLATES = {
    "qna": "qna_template_flow.json",
    "sales": "photography_flow.json",
    "ecommerce": "sneaker_shop_flow.json",
}


class TemplateService:
    """Service for managing and applying conversation flow templates."""

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.stage_service = StageService(db=db, redis=redis)

    def list_templates(self) -> list[dict]:
        """List all available templates with descriptions."""
        templates = []
        for template_id, filename in AVAILABLE_TEMPLATES.items():
            path = SEEDS_DIR / filename
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            templates.append({
                "id": template_id,
                "name": data.get("template_name", template_id),
                "description": data.get("template_description", ""),
                "stage_count": len(data.get("stages", [])),
            })
        return templates

    async def apply_template(
        self,
        tenant_id: str,
        template_id: str,
        agent_name: str,
        business_name: str,
        brand_voice: str,
    ) -> list:
        """Apply template flow to tenant.

        Deletes all existing tenant stages and replaces with template.

        Args:
            tenant_id: Tenant UUID.
            template_id: Template ID from AVAILABLE_TEMPLATES.
            agent_name: Agent name to use (e.g. "Rina", "Sari").
            business_name: Business name.
            brand_voice: Communication style (e.g. "ramah dan profesional").

        Returns:
            List of created stages.

        Raises:
            ValueError: If template_id not found.
        """
        if template_id not in AVAILABLE_TEMPLATES:
            raise ValueError(
                f"Template '{template_id}' not found. "
                f"Available: {list(AVAILABLE_TEMPLATES.keys())}"
            )

        filename = AVAILABLE_TEMPLATES[template_id]
        path = SEEDS_DIR / filename

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stages_data = data.get("stages", [])

        # Inject agent_name, business_name, brand_voice into instructions
        enriched_stages = []
        for stage in stages_data:
            enriched_instructions = (
                f"Kamu adalah {agent_name}, asisten virtual untuk {business_name}.\n"
                f"Gaya komunikasi: {brand_voice}\n\n"
                f"{stage['instructions']}"
            )
            enriched_stages.append(
                StageConfigCreate(
                    stage_id=stage["stage_id"],
                    stage_name=stage["stage_name"],
                    stage_order=stage["stage_order"],
                    goal=stage["goal"],
                    instructions=enriched_instructions,
                    required_fields=stage.get("required_fields", []),
                    next_stage=stage.get("next_stage"),
                    fallback_stage=stage.get("fallback_stage", "greeting"),
                )
            )

        result = await self.stage_service.replace_all_stages(tenant_id, enriched_stages)

        logger.info(
            "Template applied",
            tenant_id=tenant_id,
            template_id=template_id,
            stage_count=len(result),
        )

        return result
