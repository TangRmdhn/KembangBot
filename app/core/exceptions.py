"""Custom exceptions for Kembang AI.

All exceptions inherit from KembangError for consistent error handling
across the application.
"""


class KembangError(Exception):
    """Base exception for all Kembang AI errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class TenantNotFoundError(KembangError):
    """Raised when WAHA session doesn't map to any tenant."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"No tenant found for WAHA session: {session_id}",
            code="TENANT_NOT_FOUND",
            status_code=404,
        )
        self.session_id = session_id


class ConversationNotFoundError(KembangError):
    """Raised when conversation ID doesn't exist."""

    def __init__(self, conversation_id: str):
        super().__init__(
            message=f"Conversation not found: {conversation_id}",
            code="CONVERSATION_NOT_FOUND",
            status_code=404,
        )
        self.conversation_id = conversation_id


class StageConfigNotFoundError(KembangError):
    """Raised when tenant has no stage config."""

    def __init__(self, tenant_id: str):
        super().__init__(
            message=f"No stage config found for tenant: {tenant_id}",
            code="STAGE_CONFIG_NOT_FOUND",
            status_code=404,
        )
        self.tenant_id = tenant_id


class StageTransitionError(KembangError):
    """Raised when attempting invalid stage transition."""

    def __init__(self, current: str, target: str):
        super().__init__(
            message=f"Invalid stage transition from '{current}' to '{target}'",
            code="INVALID_STAGE_TRANSITION",
            status_code=400,
        )
        self.current_stage = current
        self.target_stage = target


class WebhookVerificationError(KembangError):
    """Raised when HMAC signature verification fails."""

    def __init__(self):
        super().__init__(
            message="Invalid webhook signature",
            code="WEBHOOK_INVALID_SIGNATURE",
            status_code=401,
        )


class RateLimitExceededError(KembangError):
    """Raised when customer exceeds message rate limit."""

    def __init__(self, customer_phone: str):
        super().__init__(
            message=f"Rate limit exceeded for customer: {customer_phone}",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )
        self.customer_phone = customer_phone


class WAHAError(KembangError):
    """Raised when WAHA API call fails."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="WAHA_API_ERROR",
            status_code=502,
        )


class CatalogUploadError(KembangError):
    """Raised when CSV parsing or embedding fails."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Catalog upload failed: {reason}",
            code="CATALOG_UPLOAD_ERROR",
            status_code=400,
        )
        self.reason = reason


class AuthenticationError(KembangError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid or missing authentication token"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
        )
