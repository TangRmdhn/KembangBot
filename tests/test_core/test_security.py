"""Tests for security functions."""

import pytest
import hmac
import hashlib
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request

from app.core.security import verify_waha_hmac, verify_api_key
from app.core.exceptions import WebhookVerificationError, AuthenticationError
from app.config import settings


@pytest.mark.asyncio
async def test_verify_hmac_valid():
    """Test valid HMAC signature passes verification."""
    body = b'{"test": "data"}'
    signature = hmac.new(
        settings.WAHA_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()

    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=body)
    mock_request.headers = {
        "X-Webhook-Hmac": signature,
        "X-Webhook-Hmac-Algorithm": "sha512",
    }

    result = await verify_waha_hmac(mock_request)
    assert result == body


@pytest.mark.asyncio
async def test_verify_hmac_invalid():
    """Test invalid HMAC signature raises error."""
    body = b'{"test": "data"}'

    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=body)
    mock_request.headers = {
        "X-Webhook-Hmac": "invalid_signature",
        "X-Webhook-Hmac-Algorithm": "sha512",
    }

    with pytest.raises(WebhookVerificationError):
        await verify_waha_hmac(mock_request)


@pytest.mark.asyncio
async def test_verify_hmac_missing_header():
    """Test missing HMAC header raises error."""
    body = b'{"test": "data"}'

    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=body)
    mock_request.headers = {}

    with pytest.raises(WebhookVerificationError):
        await verify_waha_hmac(mock_request)


@pytest.mark.asyncio
async def test_verify_api_key_valid():
    """Test valid API key passes verification."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        "Authorization": f"Bearer {settings.APP_SECRET_KEY}"
    }

    result = await verify_api_key(mock_request)
    assert result == "mvp-tenant-id"


@pytest.mark.asyncio
async def test_verify_api_key_with_tenant():
    """Test API key with tenant_id format."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        "Authorization": f"Bearer {settings.APP_SECRET_KEY}:tenant-123"
    }

    result = await verify_api_key(mock_request)
    assert result == "tenant-123"


@pytest.mark.asyncio
async def test_verify_api_key_invalid():
    """Test invalid API key raises error."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        "Authorization": "Bearer invalid_key"
    }

    with pytest.raises(AuthenticationError):
        await verify_api_key(mock_request)


@pytest.mark.asyncio
async def test_verify_api_key_missing_header():
    """Test missing Authorization header raises error."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}

    with pytest.raises(AuthenticationError):
        await verify_api_key(mock_request)
