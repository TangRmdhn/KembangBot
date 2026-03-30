"""Conversation service for Kembang AI.

Handles conversation CRUD and message management.
"""

from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.conversation import Conversation
from app.models.message import Message
from app.core.exceptions import ConversationNotFoundError


class ConversationService:
    """Service for conversation operations.

    Attributes:
        db: Async SQLAlchemy session.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self, tenant_id: str, customer_phone: str
    ) -> Conversation:
        """Get active conversation or create new one.

        Args:
            tenant_id: Tenant UUID.
            customer_phone: Customer's WhatsApp phone.

        Returns:
            Existing or newly created conversation.
        """
        # Look for active conversation
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.customer_phone == customer_phone,
                Conversation.status == "active",
            )
        )
        conversation = result.scalar_one_or_none()

        if conversation:
            logger.debug(
                "Found existing conversation",
                tenant_id=tenant_id,
                conversation_id=str(conversation.id),
            )
            return conversation

        # Create new conversation
        conversation = Conversation(
            tenant_id=tenant_id,
            customer_phone=customer_phone,
            current_stage="greeting",
            collected_fields={},
            status="active",
        )
        self.db.add(conversation)
        await self.db.flush()

        logger.info(
            "Created new conversation",
            tenant_id=tenant_id,
            conversation_id=str(conversation.id),
        )
        return conversation

    async def get_by_id(
        self, conversation_id: str, tenant_id: str
    ) -> Conversation:
        """Get conversation by ID with tenant scope.

        Args:
            conversation_id: Conversation UUID.
            tenant_id: Tenant UUID for scoping.

        Returns:
            Conversation instance.

        Raises:
            ConversationNotFoundError: If not found.
        """
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ConversationNotFoundError(conversation_id)

        return conversation

    async def update_state(
        self,
        conversation_id: str,
        current_stage: str,
        collected_fields: dict,
    ) -> Conversation:
        """Update conversation state after graph invocation.

        Args:
            conversation_id: Conversation UUID.
            current_stage: New current stage.
            collected_fields: Updated collected fields.

        Returns:
            Updated conversation.
        """
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one()

        conversation.current_stage = current_stage
        conversation.collected_fields = collected_fields
        conversation.last_message_at = datetime.utcnow()

        await self.db.flush()
        logger.info(
            "Conversation state updated",
            conversation_id=str(conversation_id),
            stage=current_stage,
        )
        return conversation

    async def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        waha_message_id: str | None = None,
    ) -> Message:
        """Append a message to conversation.

        Args:
            conversation_id: Conversation UUID.
            role: Message role ("human" or "ai").
            content: Message text.
            waha_message_id: Optional WAHA message ID.

        Returns:
            Created message.
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            waha_message_id=waha_message_id,
        )
        self.db.add(message)

        # Update conversation's last_message_at
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one()
        conversation.last_message_at = datetime.utcnow()

        await self.db.flush()
        return message

    async def list_by_tenant(
        self,
        tenant_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Conversation], int]:
        """List conversations for tenant with filtering.

        Args:
            tenant_id: Tenant UUID.
            status: Optional status filter.
            page: Page number.
            per_page: Items per page.

        Returns:
            Tuple of (conversations list, total count).
        """
        offset = (page - 1) * per_page

        # Build query
        query = select(Conversation).where(Conversation.tenant_id == tenant_id)
        if status:
            query = query.where(Conversation.status == status)

        # Get total count
        count_query = select(func.count()).select_from(Conversation).where(
            Conversation.tenant_id == tenant_id
        )
        if status:
            count_query = count_query.where(Conversation.status == status)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(Conversation.last_message_at.desc())
        query = query.offset(offset).limit(per_page)
        result = await self.db.execute(query)
        conversations = result.scalars().all()

        return list(conversations), total

    async def mark_handoff(self, conversation_id: str) -> Conversation:
        """Mark conversation for human handoff.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Updated conversation.
        """
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one()

        conversation.status = "handoff"
        await self.db.flush()

        logger.info(
            "Conversation marked for handoff",
            conversation_id=str(conversation_id),
        )
        return conversation

    async def get_chat_history(
        self, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        """Get last N messages from conversation.

        Args:
            conversation_id: Conversation UUID.
            limit: Number of messages to retrieve.

        Returns:
            List of messages ordered by created_at.
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
