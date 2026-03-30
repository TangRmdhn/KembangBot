"""Tests for WAHA webhook handler."""

import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

from app.config import settings


@pytest.mark.asyncio
async def test_webhook_valid_message(client, waha_message_payload, waha_hmac_signature):
    """Test webhook with valid payload and HMAC returns 200."""
    with patch("app.api.webhook.process_message"):
        response = await client.post(
            "/webhook/waha",
            json=waha_message_payload,
            headers={
                "X-Webhook-Hmac": waha_hmac_signature,
                "X-Webhook-Hmac-Algorithm": "sha512",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True


@pytest.mark.asyncio
async def test_webhook_invalid_hmac(client, waha_message_payload):
    """Test webhook with wrong HMAC signature returns 401."""
    response = await client.post(
        "/webhook/waha",
        json=waha_message_payload,
        headers={
            "X-Webhook-Hmac": "invalid_signature",
            "X-Webhook-Hmac-Algorithm": "sha512",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_ignores_own_messages(client, waha_hmac_signature):
    """Test webhook ignores messages where fromMe is true."""
    payload = {
        "event": "message",
        "session": "test_session",
        "payload": {
            "from": "6281234567890@c.us",
            "fromMe": True,
            "body": "Test message",
        },
    }

    response = await client.post(
        "/webhook/waha",
        json=payload,
        headers={
            "X-Webhook-Hmac": waha_hmac_signature,
            "X-Webhook-Hmac-Algorithm": "sha512",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("skipped") == "own_message"


@pytest.mark.asyncio
async def test_webhook_ignores_non_message_events(client, waha_hmac_signature):
    """Test webhook ignores non-message events."""
    payload = {
        "event": "message.ack",
        "session": "test_session",
        "payload": {"id": "msg_123"},
    }

    response = await client.post(
        "/webhook/waha",
        json=payload,
        headers={
            "X-Webhook-Hmac": waha_hmac_signature,
            "X-Webhook-Hmac-Algorithm": "sha512",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("skipped") == "not_a_message"


@pytest.mark.asyncio
async def test_webhook_unknown_session(client, waha_hmac_signature):
    """Test webhook handles unknown session gracefully."""
    payload = {
        "event": "message",
        "session": "unknown_session_xyz",
        "payload": {
            "from": "6281234567890@c.us",
            "fromMe": False,
            "body": "Test message",
        },
    }

    with patch("app.api.webhook.TenantService") as mock_tenant_service:
        mock_tenant_service.return_value.get_by_session = AsyncMock(return_value=None)
        
        response = await client.post(
            "/webhook/waha",
            json=payload,
            headers={
                "X-Webhook-Hmac": waha_hmac_signature,
                "X-Webhook-Hmac-Algorithm": "sha512",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("error") == "unknown_session"
