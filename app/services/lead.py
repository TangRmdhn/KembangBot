"""Lead service for Kembang AI.

Handles lead CRUD operations and status transitions.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate
from app.core.exceptions import StageTransitionError


class LeadService:
    """Service for lead operations.

    Attributes:
        db: Async SQLAlchemy session.
    """

    # Valid status transitions
    VALID_TRANSITIONS = {
        "new": ["contacted"],
        "contacted": ["negotiating", "closed_lost"],
        "negotiating": ["closed_won", "closed_lost"],
        "closed_won": [],  # Terminal
        "closed_lost": ["new"],  # Allow re-open
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: str, data: LeadCreate) -> Lead:
        """Create a new lead.

        Args:
            tenant_id: Tenant UUID.
            data: Lead creation data.

        Returns:
            Created lead.
        """
        lead = Lead(
            tenant_id=tenant_id,
            **data.model_dump(exclude={"conversation_id"}),
        )
        if data.conversation_id:
            # Will be linked via conversation_id
            lead.conversation_id = data.conversation_id

        self.db.add(lead)
        await self.db.flush()

        logger.info(
            "Lead created",
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            customer=data.customer_name,
        )
        return lead

    async def update(
        self, tenant_id: str, lead_id: str, data: LeadUpdate
    ) -> Lead:
        """Update lead with status transition validation.

        Args:
            tenant_id: Tenant UUID.
            lead_id: Lead UUID.
            data: Update data.

        Returns:
            Updated lead.

        Raises:
            StageTransitionError: If status transition is invalid.
        """
        result = await self.db.execute(
            select(Lead).where(
                Lead.id == lead_id,
                Lead.tenant_id == tenant_id,
            )
        )
        lead = result.scalar_one()

        update_data = data.model_dump(exclude_unset=True)

        # Validate status transition
        if "status" in update_data:
            new_status = update_data["status"]
            valid_next = self.VALID_TRANSITIONS.get(lead.status, [])
            if new_status not in valid_next:
                raise StageTransitionError(lead.status, new_status)

        for field, value in update_data.items():
            setattr(lead, field, value)

        await self.db.flush()

        logger.info(
            "Lead updated",
            tenant_id=tenant_id,
            lead_id=lead_id,
            status=lead.status,
        )
        return lead

    async def get_by_id(self, tenant_id: str, lead_id: str) -> Lead:
        """Get lead by ID with tenant scope.

        Args:
            tenant_id: Tenant UUID.
            lead_id: Lead UUID.

        Returns:
            Lead instance.
        """
        result = await self.db.execute(
            select(Lead).where(
                Lead.id == lead_id,
                Lead.tenant_id == tenant_id,
            )
        )
        lead = result.scalar_one()
        return lead

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Lead], int]:
        """List leads for tenant with filtering.

        Args:
            tenant_id: Tenant UUID.
            status: Optional status filter.
            page: Page number.
            per_page: Items per page.

        Returns:
            Tuple of (leads list, total count).
        """
        offset = (page - 1) * per_page

        # Build query
        query = select(Lead).where(Lead.tenant_id == tenant_id)
        if status:
            query = query.where(Lead.status == status)

        # Get total count
        count_query = select(func.count()).select_from(Lead).where(
            Lead.tenant_id == tenant_id
        )
        if status:
            count_query = count_query.where(Lead.status == status)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(Lead.created_at.desc())
        query = query.offset(offset).limit(per_page)
        result = await self.db.execute(query)
        leads = result.scalars().all()

        return list(leads), total

    async def get_stats(self, tenant_id: str) -> dict:
        """Get lead counts by status.

        Args:
            tenant_id: Tenant UUID.

        Returns:
            Dict with status counts.
        """
        result = await self.db.execute(
            select(Lead.status, func.count())
            .where(Lead.tenant_id == tenant_id)
            .group_by(Lead.status)
        )
        rows = result.all()

        stats = {status: 0 for status in self.VALID_TRANSITIONS.keys()}
        for status, count in rows:
            stats[status] = count

        return stats
