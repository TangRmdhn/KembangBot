"""Tests for health check endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test basic health check returns OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready(client):
    """Test readiness check returns db and redis status."""
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "db" in data["data"]
    assert "redis" in data["data"]
