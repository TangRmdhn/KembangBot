"""Tests for StageService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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
async def test_get_flow_config_builds_correct_structure(stage_service, mock_db, mock_redis):
    """Test get_flow_config builds correct dict structure."""
    mock_redis.get.return_value = None

    mock_stage = MagicMock()
    mock_stage.stage_id = "greeting"
    mock_stage.stage_name = "Salam"
    mock_stage.stage_order = 0
    mock_stage.goal = "Greet customer"
    mock_stage.instructions = "Say hello"
    mock_stage.required_fields = []
    mock_stage.next_stage = "check"
    mock_stage.fallback_stage = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_stage]
    mock_db.execute.return_value = mock_result

    config = await stage_service.get_flow_config("tenant-uuid")

    assert "stages" in config
    assert "initial_stage" in config
    assert config["initial_stage"] == "greeting"
    assert "greeting" in config["stages"]


@pytest.mark.asyncio
async def test_get_flow_config_caches_in_redis(stage_service, mock_db, mock_redis):
    """Test get_flow_config caches result in Redis."""
    mock_redis.get.return_value = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    await stage_service.get_flow_config("tenant-uuid")

    mock_redis.setex.assert_called()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == "kembang:tenant-uuid:stage_config"  # cache key


@pytest.mark.asyncio
async def test_get_flow_config_default_when_empty(stage_service, mock_db, mock_redis):
    """Test get_flow_config returns default when no stages exist."""
    mock_redis.get.return_value = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = []  # No stages
    mock_db.execute.return_value = mock_result

    config = await stage_service.get_flow_config("tenant-uuid")

    assert "greeting" in config["stages"]
    assert config["initial_stage"] == "greeting"


@pytest.mark.asyncio
async def test_create_stage_invalidates_cache(stage_service, mock_db, mock_redis):
    """Test create_stage deletes Redis cache."""
    mock_stage = MagicMock()
    mock_stage.stage_id = "test_stage"

    mock_db.flush = AsyncMock()

    with patch("app.services.stage.StageConfig", return_value=mock_stage):
        mock_db.add = MagicMock()

        data = StageConfigCreate(
            stage_id="test_stage",
            stage_name="Test",
            stage_order=0,
            goal="Test goal",
            instructions="Test",
        )

        await stage_service.create_stage("tenant-uuid", data)

        mock_redis.delete.assert_called()


@pytest.mark.asyncio
async def test_replace_all_stages(stage_service, mock_db, mock_redis):
    """Test replace_all_stages deletes old and creates new."""
    mock_db.flush = AsyncMock()

    data = [
        StageConfigCreate(
            stage_id="stage1",
            stage_name="Stage 1",
            stage_order=0,
            goal="Goal 1",
            instructions="Instr 1",
        ),
        StageConfigCreate(
            stage_id="stage2",
            stage_name="Stage 2",
            stage_order=1,
            goal="Goal 2",
            instructions="Instr 2",
        ),
    ]

    result = await stage_service.replace_all_stages("tenant-uuid", data)

    assert len(result) == 2
    mock_redis.delete.assert_called()  # Cache invalidated


@pytest.mark.asyncio
async def test_reorder_stages(stage_service, mock_db, mock_redis):
    """Test reorder_stages updates stage_order."""
    await stage_service.reorder_stages("tenant-uuid", ["stage1", "stage2", "stage3"])

    # Verify execute was called for each stage
    assert mock_db.execute.call_count == 3
    mock_redis.delete.assert_called()
