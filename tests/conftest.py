"""Shared fixtures for Kembang AI tests."""

import pytest
import hmac
import hashlib
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_tenant():
    """Sample tenant data for testing."""
    return {
        "business_name": "Lensa Indah Photography",
        "waha_session_id": "lensa_indah_session",
        "agent_name": "Rina",
        "brand_voice": "Santai, friendly, pakai emoji sesekali",
        "business_type": "service",
    }


@pytest.fixture
def waha_message_payload():
    """Realistic WAHA webhook payload for testing."""
    return {
        "event": "message",
        "session": "lensa_indah_session",
        "engine": "NOWEB",
        "payload": {
            "id": "true_6281234567890@c.us_AAAA",
            "timestamp": 1667561485,
            "from": "6281234567890@c.us",
            "fromMe": False,
            "body": "Halo, mau tanya soal paket foto wedding",
            "hasMedia": False,
        },
    }


@pytest.fixture
def waha_hmac_signature(waha_message_payload):
    """Compute valid HMAC signature for WAHA payload."""
    import json
    body = json.dumps(waha_message_payload).encode()
    signature = hmac.new(
        settings.WAHA_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()
    return signature
