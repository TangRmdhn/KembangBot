"""Tests for Stage API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.stage import StageConfigCreate


@pytest.mark.asyncio
async def test_list_stages(client):
    """Test GET /api/v1/stages/ returns ordered list."""
    with patch("app.api.stages.get_stage_service") as mock_service_factory:
        mock_service = AsyncMock()
        mock_service.list_stages.return_value = []
        mock_service_factory.return_value = mock_service

        response = await client.get(
            "/api/v1/stages/",
            headers={"Authorization": "Bearer test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []


@pytest.mark.asyncio
async def test_save_full_flow(client):
    """Test PUT /api/v1/stages/flow replaces entire flow."""
    stages_data = [
        {
            "stage_id": "greeting",
            "stage_name": "Salam",
            "stage_order": 0,
            "goal": "Greet",
            "instructions": "Say hi",
            "required_fields": [],
            "next_stage": "check",
            "fallback_stage": "greeting",
        },
        {
            "stage_id": "check",
            "stage_name": "Check",
            "stage_order": 1,
            "goal": "Check needs",
            "instructions": "Ask questions",
            "required_fields": ["need"],
            "next_stage": None,
            "fallback_stage": "greeting",
        },
    ]

    with patch("app.api.stages.get_stage_service") as mock_service_factory:
        mock_service = AsyncMock()
        mock_stage = MagicMock()
        mock_service.replace_all_stages.return_value = [mock_stage, mock_stage]
        mock_service_factory.return_value = mock_service

        response = await client.put(
            "/api/v1/stages/flow",
            json=stages_data,
            headers={"Authorization": "Bearer test-key"},
        )

        assert response.status_code == 200
        mock_service.replace_all_stages.assert_called_once()


@pytest.mark.asyncio
async def test_get_flow_config_via_api(client):
    """Test GET /api/v1/stages/flow-config returns compiled config."""
    with patch("app.api.stages.get_stage_service") as mock_service_factory:
        mock_service = AsyncMock()
        mock_service.get_flow_config.return_value = {
            "stages": {
                "greeting": {
                    "stage_id": "greeting",
                    "stage_name": "Salam",
                    "stage_order": 0,
                    "goal": "Greet",
                    "instructions": "Say hi",
                    "required_fields": [],
                    "next_stage": None,
                    "fallback_stage": "greeting",
                }
            },
            "initial_stage": "greeting",
        }
        mock_service_factory.return_value = mock_service

        response = await client.get(
            "/api/v1/stages/flow-config",
            headers={"Authorization": "Bearer test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "stages" in data["data"]
        assert "initial_stage" in data["data"]
