"""WAHA client for Kembang AI.

Async HTTP client for interacting with WAHA WhatsApp API.
"""

import httpx
import base64
import json
from loguru import logger

from app.config import settings
from app.core.exceptions import WAHAError


# Mock QR code for testing (1x1 pixel PNG base64)
MOCK_QR_CODE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


class WAHAClient:
    """Async client for WAHA WhatsApp HTTP API.

    Attributes:
        client: HTTPX async client.
    """

    def __init__(self):
        self.mock_mode = settings.WAHA_MOCK_MODE
        
        if self.mock_mode:
            logger.warning("WAHA running in MOCK MODE - no real WhatsApp connection")
            return
            
        if not settings.WAHA_BASE_URL:
            logger.warning("WAHA_BASE_URL not configured")
        
        # Prepare headers based on WAHA API key format
        headers = {"Content-Type": "application/json"}
        
        if settings.WAHA_API_KEY:
            # WAHA uses Bearer token auth
            # Remove "sha512:" prefix if present for Bearer token
            api_key = settings.WAHA_API_KEY
            if api_key.startswith("sha512:"):
                # For some WAHA versions, use the full key including prefix
                pass
            headers["Authorization"] = f"Bearer {api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=settings.WAHA_BASE_URL.rstrip('/') if settings.WAHA_BASE_URL else "http://localhost:3000",
            timeout=30.0,
            headers=headers,
        )
        logger.info(
            "WAHA client initialized",
            base_url=settings.WAHA_BASE_URL,
            has_api_key=bool(settings.WAHA_API_KEY),
        )

    async def test_connection(self) -> bool:
        """Test WAHA connection and authentication.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            response = await self.client.get("/api/sessions")
            if response.status_code == 200:
                logger.info("WAHA connection test successful")
                return True
            else:
                logger.warning(
                    "WAHA connection test failed",
                    status=response.status_code,
                    response=response.text[:200],
                )
                return False
        except Exception as e:
            logger.error("WAHA connection test error", error=str(e))
            return False

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
        # Mock mode for testing
        if self.mock_mode:
            # Simulate session status progression
            import random
            statuses = ["pending", "pending", "pending", "scanned", "authenticated"]
            status = random.choice(statuses)
            
            return {
                "session": session,
                "status": status.upper() if status != "pending" else "CONNECTING",
                "phone": {"wa_id": "+628123456789"} if status == "authenticated" else None,
            }
        
        try:
            response = await self.client.get(f"/api/sessions/{session}/")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise WAHAError(f"Failed to get session status: {e.response.status_code}")

    async def start_session(self, session_id: str) -> dict:
        """Start a new WAHA session (triggers QR code generation).

        Args:
            session_id: Unique session identifier.

        Returns:
            Session start response with QR code info.
        """
        # Mock mode for testing
        if self.mock_mode:
            logger.info("MOCK MODE: Starting session", session_id=session_id)
            return {
                "session": session_id,
                "status": "pending",
                "qrCode": MOCK_QR_CODE,
                "message": "Mock QR code - scan with any QR scanner for testing",
            }
        
        try:
            # Try multiple endpoint variations for WAHA compatibility
            endpoints = [
                ("POST", f"/api/sessions/{session_id}/start", {"session": session_id}),
                ("POST", f"/api/sessions/start", {"session": session_id}),
                ("GET", f"/api/sessions/{session_id}/start", None),
            ]
            
            last_error = None
            for method, endpoint, payload in endpoints:
                try:
                    if method == "POST":
                        response = await self.client.post(endpoint, json=payload)
                    else:
                        response = await self.client.get(endpoint)
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info("Session started", session_id=session_id, endpoint=endpoint)
                        return result
                    elif response.status_code == 404:
                        continue  # Try next endpoint
                    else:
                        response.raise_for_status()
                        
                except httpx.HTTPStatusError as e:
                    last_error = e
                    if e.response.status_code != 404:
                        continue
            
            # If all endpoints fail, raise the last error
            if last_error:
                raise last_error
                
            raise WAHAError(f"Failed to start session: all endpoints returned 404")

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to start session",
                session_id=session_id,
                status=e.response.status_code,
                response=e.response.text[:200] if e.response.text else "No response",
            )
            raise WAHAError(f"Failed to start session: {e.response.status_code} - {e.response.text[:100] if e.response.text else 'No response'}")
        except Exception as e:
            logger.error(
                "Failed to start session",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def get_qr_code(self, session_id: str) -> dict:
        """Get QR code for session authentication.

        Args:
            session_id: Session identifier.

        Returns:
            QR code data (base64 image or URL).
        """
        # Mock mode for testing
        if self.mock_mode:
            logger.info("MOCK MODE: Getting QR code", session_id=session_id)
            return {
                "qrCode": MOCK_QR_CODE,
                "session": session_id,
                "status": "pending",
            }
        
        try:
            # Try multiple endpoint variations for WAHA compatibility
            endpoints_to_try = [
                ("GET", f"/api/sessions/{session_id}/qr", None),
                ("GET", f"/api/sessions/{session_id}/qrCode", None),
                ("POST", f"/api/sessions/{session_id}/qr", {"session": session_id}),
            ]

            for method, endpoint, payload in endpoints_to_try:
                try:
                    if method == "GET":
                        response = await self.client.get(endpoint)
                    else:
                        response = await self.client.post(endpoint, json=payload)

                    if response.status_code == 200:
                        result = response.json()
                        logger.debug("QR code retrieved", session_id=session_id, endpoint=endpoint)
                        return result
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        continue  # Try next endpoint
                    raise

            # If all endpoints fail, try getting session status which might include QR
            response = await self.client.get(f"/api/sessions/{session_id}/")
            response.raise_for_status()
            result = response.json()

            logger.debug("Session status retrieved (may include QR)", session_id=session_id)
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to get QR code",
                session_id=session_id,
                status=e.response.status_code,
            )
            raise WAHAError(f"Failed to get QR code: {e.response.status_code}")

    async def stop_session(self, session_id: str) -> dict:
        """Stop a WAHA session.

        Args:
            session_id: Session identifier.

        Returns:
            Session stop response.
        """
        try:
            response = await self.client.post(
                f"/api/sessions/{session_id}/stop",
                json={"session": session_id},
            )
            response.raise_for_status()
            result = response.json()

            logger.info("Session stopped", session_id=session_id)
            return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to stop session",
                session_id=session_id,
                status=e.response.status_code,
            )
            raise WAHAError(f"Failed to stop session: {e.response.status_code}")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("WAHA client closed")
