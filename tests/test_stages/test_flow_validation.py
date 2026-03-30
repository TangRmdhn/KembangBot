"""Tests for flow validation."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_valid_flow(client):
    """Test validation passes for complete flow."""
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

    response = await client.post(
        "/api/v1/stages/validate",
        json=stages_data,
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_empty_flow(client):
    """Test validation fails for empty flow."""
    response = await client.post(
        "/api/v1/stages/validate",
        json=[],
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "at least one stage" in data["errors"][0]


@pytest.mark.asyncio
async def test_duplicate_stage_ids(client):
    """Test validation fails for duplicate stage_ids."""
    stages_data = [
        {
            "stage_id": "greeting",
            "stage_name": "Salam",
            "stage_order": 0,
            "goal": "Greet",
            "instructions": "Say hi",
            "required_fields": [],
            "next_stage": None,
            "fallback_stage": "greeting",
        },
        {
            "stage_id": "greeting",  # Duplicate!
            "stage_name": "Greeting 2",
            "stage_order": 1,
            "goal": "Greet again",
            "instructions": "Say hi again",
            "required_fields": [],
            "next_stage": None,
            "fallback_stage": "greeting",
        },
    ]

    response = await client.post(
        "/api/v1/stages/validate",
        json=stages_data,
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "Duplicate" in data["errors"][0]


@pytest.mark.asyncio
async def test_invalid_next_stage_reference(client):
    """Test validation fails for invalid next_stage reference."""
    stages_data = [
        {
            "stage_id": "greeting",
            "stage_name": "Salam",
            "stage_order": 0,
            "goal": "Greet",
            "instructions": "Say hi",
            "required_fields": [],
            "next_stage": "nonexistent",  # Invalid reference
            "fallback_stage": "greeting",
        },
    ]

    response = await client.post(
        "/api/v1/stages/validate",
        json=stages_data,
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "unknown next_stage" in data["errors"][0]


@pytest.mark.asyncio
async def test_warning_required_fields_on_first_stage(client):
    """Test validation warns if first stage has required_fields."""
    stages_data = [
        {
            "stage_id": "greeting",
            "stage_name": "Salam",
            "stage_order": 0,
            "goal": "Greet",
            "instructions": "Say hi",
            "required_fields": ["name"],  # Warning!
            "next_stage": None,
            "fallback_stage": "greeting",
        },
    ]

    response = await client.post(
        "/api/v1/stages/validate",
        json=stages_data,
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True  # Still valid, just a warning
    assert any("required_fields" in w for w in data["warnings"])


@pytest.mark.asyncio
async def test_circular_reference_allowed(client):
    """Test circular references are allowed (intentional for fallbacks)."""
    stages_data = [
        {
            "stage_id": "greeting",
            "stage_name": "Salam",
            "stage_order": 0,
            "goal": "Greet",
            "instructions": "Say hi",
            "required_fields": [],
            "next_stage": "check",
            "fallback_stage": "greeting",  # Self-reference for fallback
        },
        {
            "stage_id": "check",
            "stage_name": "Check",
            "stage_order": 1,
            "goal": "Check needs",
            "instructions": "Ask questions",
            "required_fields": [],
            "next_stage": "greeting",  # Back to greeting
            "fallback_stage": "greeting",
        },
    ]

    response = await client.post(
        "/api/v1/stages/validate",
        json=stages_data,
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True  # Circular refs are allowed
