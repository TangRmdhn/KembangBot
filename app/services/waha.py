"""WAHA client for Kembang AI.

Async HTTP client for interacting with WAHA WhatsApp API.
"""

import httpx
from loguru import logger

from app.config import settings
from app.core.exceptions import WAHAError


class WAHAClient:
    """Async client for WAHA WhatsApp HTTP API.

    Attributes:
        client: HTTPX async client.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=settings.WAHA_BASE_URL,
            timeout=30.0,
            headers={"Authorization": f"Bearer {settings.WAHA_API_KEY}"}
            if settings.WAHA_API_KEY
            else {},
        )

    async def send_text(self, session: str, chat_id: str, text: str) -> dict:
        """Send a text message via WAHA API.

        Args:
            session: WAHA session name.
            chat_id: WhatsApp chat ID (e.g., "6281234567890@c.us").
            text: Message text to send.

        Returns:
            WAHA API response.

        Raises:
            WAHAError: If the API call fails.
        """
        try:
            response = await self.client.post(
                "/api/sendText",
                json={"session": session, "chatId": chat_id, "text": text},
            )
            response.raise_for_status()
            result = response.json()

            logger.debug(
                "Message sent via WAHA",
                session=session,
                chat_id=chat_id,
                text_length=len(text),
            )
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "WAHA send failed",
                status=e.response.status_code,
                session=session,
            )
            raise WAHAError(f"Failed to send message: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("WAHA request error", error=str(e))
            raise WAHAError(f"WAHA connection error: {str(e)}")

    async def send_image(
        self, session: str, chat_id: str, image_url: str, caption: str = ""
    ) -> dict:
        """Send an image message via WAHA API.

        Args:
            session: WAHA session name.
            chat_id: WhatsApp chat ID.
            image_url: URL of the image to send.
            caption: Optional caption text.

        Returns:
            WAHA API response.

        Raises:
            WAHAError: If the API call fails.
        """
        try:
            response = await self.client.post(
                "/api/sendImage",
                json={
                    "session": session,
                    "chatId": chat_id,
                    "url": image_url,
                    "caption": caption,
                },
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise WAHAError(f"Failed to send image: {e.response.status_code}")

    async def send_seen(self, session: str, chat_id: str) -> dict:
        """Mark message as read via WAHA API.

        Args:
            session: WAHA session name.
            chat_id: WhatsApp chat ID.

        Returns:
            WAHA API response.
        """
        try:
            response = await self.client.post(
                "/api/sendSeen",
                json={"session": session, "chatId": chat_id},
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError:
            # Don't raise for seen - it's not critical
            logger.warning("Failed to send seen", session=session)
            return {}

    async def get_session_status(self, session: str) -> dict:
        """Get WAHA session status.

        Args:
            session: WAHA session name.

        Returns:
            Session status info.
        """
        try:
            response = await self.client.get(f"/api/sessions/{session}/")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise WAHAError(f"Failed to get session status: {e.response.status_code}")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("WAHA client closed")
