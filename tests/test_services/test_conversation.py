"""Tests for ConversationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.conversation import ConversationService
from app.core.exceptions import ConversationNotFoundError


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def conversation_service(mock_db):
    """Create ConversationService with mocked DB."""
    return ConversationService(db=mock_db)


@pytest.mark.asyncio
async def test_get_or_create_new(conversation_service, mock_db):
    """Test get_or_create creates new conversation when none exists."""
    # No existing conversation
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.flush = AsyncMock()

    with patch("app.services.conversation.Conversation") as mock_conversation_class:
        mock_conversation = MagicMock()
        mock_conversation.id = "new-uuid"
        mock_conversation_class.return_value = mock_conversation

        mock_db.add = MagicMock()

        conversation = await conversation_service.get_or_create(
            tenant_id="tenant-uuid",
            customer_phone="6281234567890@c.us",
        )

        assert mock_db.add.called
        assert conversation is not None


@pytest.mark.asyncio
async def test_get_or_create_existing(conversation_service, mock_db):
    """Test get_or_create returns existing active conversation."""
    mock_conversation = MagicMock()
    mock_conversation.id = "existing-uuid"
    mock_conversation.status = "active"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_conversation
    mock_db.execute.return_value = mock_result

    conversation = await conversation_service.get_or_create(
        tenant_id="tenant-uuid",
        customer_phone="6281234567890@c.us",
    )

    assert conversation.id == "existing-uuid"
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_save_message(conversation_service, mock_db):
    """Test saving a message to conversation."""
    mock_conversation = MagicMock()
    mock_conversation_result = MagicMock()
    mock_conversation_result.scalar_one.return_value = mock_conversation

    mock_message = MagicMock()
    mock_message.id = "msg-uuid"

    mock_db.execute = AsyncMock(side_effect=[
        mock_conversation_result,  # For getting conversation
        mock_conversation_result,  # For updating last_message_at
    ])
    mock_db.flush = AsyncMock()

    with patch("app.services.conversation.Message", return_value=mock_message):
        mock_db.add = MagicMock()

        message = await conversation_service.save_message(
            conversation_id="conv-uuid",
            role="human",
            content="Test message",
        )

        mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_mark_handoff(conversation_service, mock_db):
    """Test marking conversation for handoff."""
    mock_conversation = MagicMock()
    mock_conversation.id = "conv-uuid"

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = mock_conversation
    mock_db.execute.return_value = mock_result
    mock_db.flush = AsyncMock()

    conversation = await conversation_service.mark_handoff("conv-uuid")

    assert mock_conversation.status == "handoff"
