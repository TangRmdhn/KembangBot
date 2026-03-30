"""WAHA webhook payload schemas.

Matches the exact WAHA API format for incoming webhooks.
"""

from pydantic import BaseModel, Field, ConfigDict


class WAHAMedia(BaseModel):
    """Media attachment in WAHA message."""

    url: str | None = None
    mimetype: str | None = None
    filename: str | None = None
    error: str | None = None


class WAHAWebhookPayload(BaseModel):
    """Incoming message payload from WAHA webhook."""

    id: str
    timestamp: int
    from_: str = Field(alias="from")  # "6281234567890@c.us"
    from_me: bool = Field(alias="fromMe", default=False)
    to: str | None = None
    body: str | None = None
    has_media: bool = Field(alias="hasMedia", default=False)
    source: str | None = None  # "app" or "api"
    ack: int | None = None
    media: WAHAMedia | None = None

    model_config = ConfigDict(populate_by_name=True)


class WAHAWebhookEvent(BaseModel):
    """Top-level WAHA webhook event."""

    event: str  # "message", "message.ack", "session.status", etc.
    session: str  # WAHA session name
    payload: dict  # Raw payload — we parse it based on event type
    engine: str | None = None
    environment: dict | None = None
