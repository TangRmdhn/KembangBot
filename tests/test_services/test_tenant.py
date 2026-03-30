"""Tests for TenantService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.tenant import TenantService
from app.schemas.tenant import TenantCreate


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
def tenant_service(mock_db, mock_redis):
    """Create TenantService with mocked dependencies."""
    return TenantService(db=mock_db, redis=mock_redis)


@pytest.mark.asyncio
async def test_get_by_session_cached(tenant_service, mock_redis):
    """Test get_by_session returns cached tenant."""
    cached_data = {
        "id": "test-uuid",
        "business_name": "Test Business",
        "waha_session_id": "test_session",
        "agent_name": "Test Agent",
        "brand_voice": None,
        "business_type": "general",
        "phone_number": None,
        "subscription_plan": "basic",
        "is_active": True,
    }
    mock_redis.get.return_value = json.dumps(cached_data)

    tenant = await tenant_service.get_by_session("test_session")

    assert tenant is not None
    assert tenant.business_name == "Test Business"
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_session_not_found(tenant_service, mock_redis, mock_db):
    """Test get_by_session returns None for unknown session."""
    mock_redis.get.return_value = None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    tenant = await tenant_service.get_by_session("unknown_session")

    assert tenant is None


@pytest.mark.asyncio
async def test_create_tenant(tenant_service, mock_db, mock_redis):
    """Test creating a new tenant."""
    data = TenantCreate(
        business_name="New Business",
        waha_session_id="new_session",
    )

    mock_tenant = MagicMock()
    mock_tenant.id = "test-uuid"
    mock_tenant.business_name = "New Business"
    mock_tenant.waha_session_id = "new_session"

    mock_db.flush = AsyncMock()

    with patch("app.services.tenant.Tenant", return_value=mock_tenant):
        mock_db.add = MagicMock()
        tenant = await tenant_service.create(data)

        assert tenant.business_name == "New Business"
        mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_update_tenant(tenant_service, mock_db, mock_redis):
    """Test updating a tenant."""
    from app.schemas.tenant import TenantUpdate

    mock_tenant = MagicMock()
    mock_tenant.id = "test-uuid"
    mock_tenant.business_name = "Old Name"
    mock_tenant.waha_session_id = "test_session"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant
    mock_db.execute.return_value = mock_result
    mock_db.flush = AsyncMock()

    update_data = TenantUpdate(business_name="New Name")
    tenant = await tenant_service.update("test-uuid", update_data)

    assert mock_tenant.business_name == "New Name"
    mock_redis.delete.assert_called()
