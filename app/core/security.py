"""Security utilities for Kembang AI.

Provides HMAC verification for WAHA webhooks and simple API key
authentication for dashboard endpoints.
"""

import hmac
import hashlib
from fastapi import Request

from app.config import settings
from app.core.exceptions import WebhookVerificationError, AuthenticationError


async def verify_waha_hmac(request: Request) -> bytes:
    """Verify WAHA webhook HMAC-SHA512 signature.

    Reads the raw request body, computes HMAC using the shared secret,
    and compares with the X-Webhook-Hmac header from WAHA.

    Args:
        request: FastAPI request object.

    Returns:
        Raw body bytes if signature is valid.

    Raises:
        WebhookVerificationError: If signature is missing or invalid.
    """
    body = await request.body()
    received_hmac = request.headers.get("X-Webhook-Hmac", "")
    algorithm = request.headers.get("X-Webhook-Hmac-Algorithm", "sha512")

    if not received_hmac:
        raise WebhookVerificationError()

    # Compute expected HMAC
    expected_hmac = hmac.new(
        settings.WAHA_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()

    # Timing-safe comparison
    if not hmac.compare_digest(received_hmac, expected_hmac):
        raise WebhookVerificationError()

    return body


async def verify_api_key(request: Request) -> str:
    """Verify API key from Authorization header for dashboard endpoints.

    MVP: simple bearer token check against APP_SECRET_KEY.

    Args:
        request: FastAPI request object.

    Returns:
        Placeholder tenant_id (for MVP, just validates the key exists).

    Raises:
        AuthenticationError: If API key is missing or invalid.

    Todo:
        Replace with proper JWT auth with tenant_id extraction.
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix

    # MVP: Check against APP_SECRET_KEY
    # Format expected: "{APP_SECRET_KEY}:{tenant_id}" or just "{APP_SECRET_KEY}"
    if token == settings.APP_SECRET_KEY:
        # For MVP, return a placeholder tenant_id
        # TODO: implement JWT with tenant_id extraction
        return "mvp-tenant-id"

    # Try parsing "key:tenant_id" format
    if ":" in token:
        key, tenant_id = token.split(":", 1)
        if key == settings.APP_SECRET_KEY:
            return tenant_id

    raise AuthenticationError("Invalid API key")
