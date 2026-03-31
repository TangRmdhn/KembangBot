"""WAHA webhook handler for Kembang AI.

Receives incoming WhatsApp messages via WAHA webhook and processes
them through the LangGraph conversation engine.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from loguru import logger

from app.core.security import verify_waha_hmac
from app.core.utils import clean_phone, to_waha_chat_id
from app.services.tenant import TenantService
from app.services.conversation import ConversationService
from app.services.waha import WAHAClient
from app.services.stage import StageService
from app.agents.graph import invoke_conversation_graph
from app.schemas.webhook import WAHAWebhookEvent
from app.dependencies import (
    get_tenant_service,
    get_conversation_service,
    get_stage_service,
    get_waha_client,
)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/waha")
async def handle_waha_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    tenant_service: Annotated[TenantService, Depends(get_tenant_service)],
    conversation_service: Annotated[ConversationService, Depends(get_conversation_service)],
    stage_service: Annotated[StageService, Depends(get_stage_service)],
    waha_client: Annotated[WAHAClient, Depends(get_waha_client)],
) -> dict:
    """Handle incoming WAHA webhook events.

    This endpoint receives WhatsApp messages from WAHA, verifies the HMAC
    signature, and processes them through the LangGraph conversation engine.

    The actual message processing happens in a background task to return
    200 OK immediately to WAHA.

    Args:
        request: FastAPI request object.
        background_tasks: FastAPI background tasks.
        tenant_service: Tenant service dependency.
        conversation_service: Conversation service dependency.
        stage_service: Stage service dependency.
        waha_client: WAHA client dependency.

    Returns:
        Success response dict.
    """
    # Verify HMAC signature
    await verify_waha_hmac(request)

    # Parse webhook event
    data = await request.json()
    event = WAHAWebhookEvent(**data)

    # Handle session events (QR authentication)
    if event.event == "session":
        return await handle_session_event(
            event=event,
            tenant_service=tenant_service,
        )

    # Only process message events
    if event.event != "message":
        logger.debug("Ignoring non-message event", event=event.event)
        return {"ok": True, "skipped": "not_a_message"}

    # Parse payload
    payload = event.payload
    from_me = payload.get("fromMe", False)

    # Ignore our own messages
    if from_me:
        logger.debug("Ignoring own message")
        return {"ok": True, "skipped": "own_message"}

    # Extract message details
    session = event.session
    from_phone = payload.get("from", "")
    body = payload.get("body", "")
    waha_message_id = payload.get("id")

    if not body:
        logger.debug("Ignoring message with no body")
        return {"ok": True, "skipped": "no_body"}

    # Resolve tenant from session
    tenant = await tenant_service.get_by_session(session)
    if not tenant:
        logger.warning("Unknown WAHA session", session=session)
        return {"ok": True, "error": "unknown_session"}

    if not tenant.is_active:
        logger.warning("Inactive tenant", tenant_id=str(tenant.id))
        return {"ok": True, "error": "tenant_inactive"}

    # Process in background
    background_tasks.add_task(
        process_message,
        tenant_id=str(tenant.id),
        waha_session=session,
        customer_phone=from_phone,
        message_text=body,
        waha_message_id=waha_message_id,
        tenant_service=tenant_service,
        conversation_service=conversation_service,
        stage_service=stage_service,
        waha_client=waha_client,
    )

    logger.info(
        "Webhook received",
        session=session,
        from_phone=clean_phone(from_phone),
        message_length=len(body),
    )

    return {"ok": True}


async def handle_session_event(
    event: WAHAWebhookEvent,
    tenant_service: TenantService,
) -> dict:
    """Handle WAHA session events (QR authentication).

    When a user scans the QR code, WAHA sends a session event with
    authentication status. This handler completes the tenant creation.

    Args:
        event: WAHA webhook event.
        tenant_service: Tenant service instance.

    Returns:
        Success response dict.
    """
    payload = event.payload
    session = event.session
    status = payload.get("status")

    logger.info(
        "Session event received",
        session=session,
        status=status,
    )

    # Handle authenticated status
    if status in ["CONNECTED", "AUTHENTICATED", "opened"]:
        # Extract phone number from payload
        phone_info = payload.get("phone", {})
        phone_number = phone_info.get("wa_id") or phone_info.get("waid")

        if not phone_number:
            # Try alternative field
            phone_number = payload.get("phoneNumber") or payload.get("phone_number")

        if phone_number:
            # Complete QR authentication and create tenant
            tenant = await tenant_service.complete_qr_authentication(
                session_id=session,
                phone_number=phone_number,
            )

            if tenant:
                logger.info(
                    "QR authentication completed via webhook",
                    session=session,
                    tenant_id=str(tenant.id),
                    phone_number=phone_number,
                )
                return {"ok": True}
            else:
                logger.warning(
                    "QR session not found (might be existing tenant)",
                    session=session,
                )
        else:
            logger.warning("No phone number in session event", session=session)

    return {"ok": True}


async def process_message(
    tenant_id: str,
    waha_session: str,
    customer_phone: str,
    message_text: str,
    waha_message_id: str,
    tenant_service: TenantService,
    conversation_service: ConversationService,
    stage_service: StageService,
    waha_client: WAHAClient,
) -> None:
    """Process incoming message through LangGraph engine.

    This function runs in the background and:
    1. Gets or creates conversation
    2. Saves incoming message
    3. Invokes LangGraph engine
    4. Saves AI response
    5. Sends response via WAHA

    Args:
        tenant_id: Tenant UUID.
        waha_session: WAHA session name.
        customer_phone: Customer's WhatsApp phone.
        message_text: Incoming message text.
        waha_message_id: WAHA message ID.
        tenant_service: Tenant service.
        conversation_service: Conversation service.
        stage_service: Stage service.
        waha_client: WAHA client.
    """
    try:
        # Idempotency check — FIRST, before anything else
        if waha_message_id:
            from app.db.redis import get_redis
            redis = await get_redis()
            dedup_key = f"kembang:dedup:{waha_message_id}"
            is_new = await redis.set(dedup_key, "1", nx=True, ex=3600)  # TTL 1 hour
            if not is_new:
                logger.info(
                    "Duplicate webhook ignored",
                    waha_message_id=waha_message_id,
                    tenant_id=tenant_id,
                )
                return

        # Rate limit check
        from app.db.redis import get_redis
        from app.core.utils import check_rate_limit
        from app.config import settings

        redis = await get_redis()
        allowed = await check_rate_limit(
            redis=redis,
            tenant_id=tenant_id,
            customer_phone=clean_phone(customer_phone),
            limit_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        )

        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                tenant_id=tenant_id,
                customer_phone=clean_phone(customer_phone),
            )
            return

        # Get or create conversation
        conversation = await conversation_service.get_or_create(
            tenant_id=tenant_id,
            customer_phone=customer_phone,
        )

        # Save incoming message
        await conversation_service.save_message(
            conversation_id=str(conversation.id),
            role="human",
            content=message_text,
            waha_message_id=waha_message_id,
        )

        # Load stage config
        stage_config = await stage_service.get_flow_config(tenant_id)

        # Invoke LangGraph engine
        result = await invoke_conversation_graph(
            tenant_id=tenant_id,
            conversation=conversation,
            message_text=message_text,
            stage_config=stage_config,
        )

        # Get formatted response
        response_text = result.get("formatted_output", "")
        needs_handoff = result.get("needs_human_handoff", False)

        if not response_text:
            logger.warning("Empty response from graph", tenant_id=tenant_id)
            return

        # Save AI response
        await conversation_service.save_message(
            conversation_id=str(conversation.id),
            role="ai",
            content=response_text,
        )

        # Update conversation state
        await conversation_service.update_state(
            conversation_id=str(conversation.id),
            current_stage=result.get("current_stage", conversation.current_stage),
            collected_fields=result.get("collected_fields", conversation.collected_fields),
        )

        # Mark for handoff if needed
        if needs_handoff:
            await conversation_service.mark_handoff(str(conversation.id))

        # Save pending lead if present (from save_lead_info tool)
        pending_lead = result.get("pending_lead")
        if pending_lead and pending_lead.get("__lead_data__"):
            from app.services.lead import LeadService
            from app.schemas.lead import LeadCreate
            lead_service = LeadService(db=conversation_service.db)
            await lead_service.create(
                tenant_id=tenant_id,
                data=LeadCreate(
                    customer_phone=pending_lead.get("customer_phone", customer_phone),
                    customer_name=pending_lead.get("customer_name"),
                    notes=pending_lead.get("notes"),
                    estimated_value=pending_lead.get("estimated_value"),
                    conversation_id=str(conversation.id),
                ),
            )
            logger.info("Lead saved from pending state", tenant_id=tenant_id)

        # Send response via WAHA
        chat_id = to_waha_chat_id(clean_phone(customer_phone))
        await waha_client.send_text(
            session=waha_session,
            chat_id=chat_id,
            text=response_text,
        )

        logger.info(
            "Message processed",
            tenant_id=tenant_id,
            conversation_id=str(conversation.id),
            response_length=len(response_text),
            handoff=needs_handoff,
        )

    except Exception as e:
        logger.exception(
            "Message processing failed",
            tenant_id=tenant_id,
            customer_phone=customer_phone,
        )
