"""Tenant API routes for Kembang AI dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from loguru import logger

from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    QRSessionRequest,
    QRSessionResponse,
    QRStatusResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.services.tenant import TenantService
from app.services.waha import WAHAClient
from app.dependencies import get_tenant_service, get_current_tenant_id

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.post(
    "/qr-session",
    response_model=APIResponse[QRSessionResponse],
    status_code=201,
    summary="Start QR Code Authentication",
    description="Create a new QR session for WhatsApp Business login. "
    "Returns session_id and temp_token for polling status.",
)
async def start_qr_session(
    data: QRSessionRequest,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    waha_client: Annotated[WAHAClient, Depends()],
) -> APIResponse[QRSessionResponse]:
    """Start QR code authentication flow for new tenant.

    This endpoint:
    1. Creates a temporary session in Redis
    2. Starts WAHA session to generate QR code
    3. Returns session_id with QR code (if available)

    Client should poll /qr-session/{session_id}/status until authenticated.
    """
    from app.config import settings
    
    # Validate WAHA configuration
    if not settings.WAHA_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="WAHA_BASE_URL not configured. Please set WAHA_BASE_URL in environment variables."
        )

    # Create temporary session
    session_result = await tenant_service.create_qr_session(data)
    session_id = session_result["session_id"]

    # Start WAHA session (triggers QR generation)
    try:
        start_result = await waha_client.start_session(session_id)

        # Some WAHA versions return QR code directly in start response
        qr_code = start_result.get("qrCode") or start_result.get("qr_code") or start_result.get("qr")
        qr_type = "base64" if qr_code and qr_code.startswith("data:") else "url" if qr_code else None

        return APIResponse(
            success=True,
            data=QRSessionResponse(
                session_id=session_id,
                qr_code=qr_code,
                qr_type=qr_type or "base64",
                status="ready" if qr_code else "pending",
                expires_at=session_result["expires_at"],
            ),
            message="QR session created. QR code included if available." if qr_code 
                    else "QR session created. Fetch QR code from /qr-session/{session_id}/qr endpoint.",
        )

    except HTTPException:
        # Clean up Redis if WAHA fails
        await tenant_service.redis.delete(f"kembang:qr_session:{session_id}")
        raise
    except Exception as e:
        # Clean up Redis if WAHA fails
        await tenant_service.redis.delete(f"kembang:qr_session:{session_id}")
        logger.error(
            "Failed to start QR session",
            session_id=session_id,
            error=str(e),
            waha_url=settings.WAHA_BASE_URL,
        )
        
        # Provide helpful error message based on error type
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="WAHA authentication failed (401). Please check WAHA_API_KEY in .env file. "
                       "Ensure the API key matches your WAHA server configuration."
            )
        elif "403" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="WAHA access forbidden (403). Your API key may not have permission to create sessions."
            )
        elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to WAHA server at {settings.WAHA_BASE_URL}. "
                       "Ensure WAHA is running and accessible."
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to WAHA: {error_msg}"
            )


@router.get(
    "/qr-session/{session_id}/qr",
    response_model=APIResponse[QRSessionResponse],
    summary="Get QR Code Image",
    description="Retrieve the QR code image for scanning.",
)
async def get_qr_code(
    session_id: str,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    waha_client: Annotated[WAHAClient, Depends()],
) -> APIResponse[QRSessionResponse]:
    """Get QR code image for session authentication.

    Returns base64-encoded QR code image that can be displayed to user.
    First checks if session exists in Redis, then fetches from WAHA.
    """
    # Check if session exists in Redis
    session_data = await tenant_service.redis.get(f"kembang:qr_session:{session_id}")
    if not session_data:
        raise HTTPException(status_code=404, detail="QR session not found or expired")

    try:
        qr_result = await waha_client.get_qr_code(session_id)

        # Extract QR code from WAHA response (multiple possible formats)
        qr_code = (
            qr_result.get("qrCode") 
            or qr_result.get("qr_code") 
            or qr_result.get("qr")
            or qr_result.get("base64")
        )
        
        # Determine QR type
        qr_type = "base64" if qr_code and qr_code.startswith("data:") else "url" if qr_code else "text"

        if not qr_code:
            # Session might still be initializing
            return APIResponse(
                success=True,
                data=QRSessionResponse(
                    session_id=session_id,
                    qr_code=None,
                    qr_type="base64",
                    status="pending",
                ),
                message="QR code not yet available. Please try again in a few seconds.",
            )

        return APIResponse(
            success=True,
            data=QRSessionResponse(
                session_id=session_id,
                qr_code=qr_code,
                qr_type=qr_type,
                status="ready",
            ),
            message="QR code retrieved. Please scan with WhatsApp Business app.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get QR code", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=503, 
            detail=f"Unable to fetch QR code from WAHA: {str(e)}. Please ensure WAHA is running."
        )


@router.get(
    "/qr-session/{session_id}/status",
    response_model=APIResponse[QRStatusResponse],
    summary="Check QR Authentication Status",
    description="Poll this endpoint to check if QR code has been scanned.",
)
async def check_qr_status(
    session_id: str,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    waha_client: Annotated[WAHAClient, Depends()],
) -> APIResponse[QRStatusResponse]:
    """Check QR session authentication status.

    Poll this endpoint every 2-3 seconds until status becomes 'authenticated'.
    Once authenticated, tenant is automatically created.
    """
    # Check local Redis status first
    local_status = await tenant_service.get_qr_session_status(session_id)

    if local_status and local_status["status"] == "authenticated":
        return APIResponse(
            success=True,
            data=QRStatusResponse(**local_status),
            message="Authentication successful! Tenant created.",
        )

    # Check WAHA session status
    try:
        waha_status = await waha_client.get_session_status(session_id)
        status = waha_status.get("status", "pending")

        # Map WAHA status to our status
        if status in ["CONNECTED", "AUTHENTICATED"]:
            # Update local status
            phone = waha_status.get("phone", {}).get("wa_id") or waha_status.get("phone_number")

            if phone:
                await tenant_service.complete_qr_authentication(session_id, phone)
                local_status = await tenant_service.get_qr_session_status(session_id)
                return APIResponse(
                    success=True,
                    data=QRStatusResponse(**local_status),
                    message="Authentication successful! Tenant created.",
                )

        return APIResponse(
            success=True,
            data=QRStatusResponse(
                session_id=session_id,
                status="pending",
            ),
            message="Waiting for QR code scan...",
        )

    except Exception as e:
        # Session might not exist yet in WAHA
        if local_status:
            return APIResponse(
                success=True,
                data=QRStatusResponse(
                    session_id=session_id,
                    status=local_status.get("status", "pending"),
                    business_name=local_status.get("business_name"),
                ),
                message="Session initializing...",
            )
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")


@router.post("/", response_model=APIResponse[TenantResponse], status_code=201)
async def create_tenant(
    data: TenantCreate,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
) -> APIResponse[TenantResponse]:
    """Create a new tenant.

    This endpoint creates a new business tenant in the system.
    """
    tenant = await tenant_service.create(data)
    return APIResponse(
        success=True,
        data=TenantResponse.model_validate(tenant),
        message="Tenant created successfully",
    )


@router.get("/", response_model=PaginatedResponse[TenantResponse])
async def list_tenants(
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    tenant_id: Annotated[str, Depends(get_current_tenant_id)],
    page: int = 1,
    per_page: int = 20,
) -> PaginatedResponse[TenantResponse]:
    """List all tenants with pagination.

    Returns paginated list of all tenants in the system.
    """
    tenants, total = await tenant_service.list_all(page=page, per_page=per_page)

    return PaginatedResponse(
        success=True,
        data=[TenantResponse.model_validate(t) for t in tenants],
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=(total + per_page - 1) // per_page,
        ),
    )


@router.get("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def get_tenant(
    tenant_id: str,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    current_tenant: str = Depends(get_current_tenant_id),
) -> APIResponse[TenantResponse]:
    """Get a single tenant by ID.

    Returns tenant details for the specified tenant ID.
    """
    tenant = await tenant_service.get_by_id(tenant_id)
    return APIResponse(
        success=True,
        data=TenantResponse.model_validate(tenant),
    )


@router.put("/{tenant_id}", response_model=APIResponse[TenantResponse])
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    current_tenant: str = Depends(get_current_tenant_id),
) -> APIResponse[TenantResponse]:
    """Update an existing tenant.

    Partially updates tenant fields. Only provided fields are updated.
    """
    tenant = await tenant_service.update(tenant_id, data)
    return APIResponse(
        success=True,
        data=TenantResponse.model_validate(tenant),
        message="Tenant updated successfully",
    )
