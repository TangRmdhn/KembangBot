"""Tests for StageService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.stage import StageService
from app.schemas.stage import StageConfigCreate


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
def stage_service(mock_db, mock_redis):
    """Create StageService with mocked dependencies."""
    return StageService(db=mock_db, redis=mock_redis)


@pytest.mark.asyncio
async def test_get_flow_config_cached(stage_service, mock_redis):
    """Test get_flow_config returns cached config."""
    cached_config = {
        "stages": {
            "greeting": {
                "stage_id": "greeting",
                "stage_name": "Salam",
                "stage_order": 0,
                "goal": "Greet customer",
                "instructions": "Say hello",
                "required_fields": [],
                "next_stage": None,
                "fallback_stage": None,
            }
        },
        "initial_stage": "greeting",
    }
    mock_redis.get.return_value = json.dumps(cached_config)

    config = await stage_service.get_flow_config("tenant-uuid")

    assert config == cached_config
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_flow_config_default(stage_service, mock_redis, mock_db):
    """Test get_flow_config returns default when no stages exist."""
    mock_redis.get.return_value = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = []  # No stages
    mock_db.execute.return_value = mock_result

    config = await stage_service.get_flow_config("tenant-uuid")

    assert "stages" in config
    assert "greeting" in config["stages"]
    assert config["initial_stage"] == "greeting"


@pytest.mark.asyncio
async def test_create_stage(stage_service, mock_db, mock_redis):
    """Test creating a new stage."""
    data = StageConfigCreate(
        stage_id="test_stage",
        stage_name="Test Stage",
        stage_order=0,
        goal="Test goal",
        instructions="Test instructions",
    )

    mock_stage = MagicMock()
    mock_stage.id = "stage-uuid"
    mock_stage.stage_id = "test_stage"

    mock_db.flush = AsyncMock()

    with patch("app.services.stage.StageConfig", return_value=mock_stage):
        mock_db.add = MagicMock()

        stage = await stage_service.create_stage("tenant-uuid", data)

        assert stage.stage_id == "test_stage"
        mock_db.add.assert_called_once()
        mock_redis.delete.assert_called()  # Cache invalidated


@pytest.mark.asyncio
async def test_cache_invalidation_on_update(stage_service, mock_db, mock_redis):
    """Test that cache is invalidated when stage is updated."""
    mock_stage = MagicMock()
    mock_stage.stage_id = "greeting"
    mock_stage.stage_name = "Old Name"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_stage
    mock_db.execute.return_value = mock_result
    mock_db.flush = AsyncMock()

    from app.schemas.stage import StageConfigUpdate
    update_data = StageConfigUpdate(stage_name="New Name")

    await stage_service.update_stage("tenant-uuid", "greeting", update_data)

    mock_redis.delete.assert_called()
