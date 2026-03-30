"""LangGraph tool definitions for Kembang AI conversation engine.

Tools give the conversation agent access to external data:
product catalog search, pricing rules, and lead management.
Tools are defined using LangChain's @tool decorator.
"""

import json
import uuid
from loguru import logger
from langchain_core.tools import tool


@tool
async def search_catalog(query: str, tenant_id: str) -> str:
    """Search the tenant's product or service catalog for relevant items.

    Use this tool when:
    - Customer asks about available products/services
    - Customer asks about pricing
    - You need to recommend products/packages based on customer needs
    - Customer asks about specifications, features, or availability

    Args:
        query: Natural language search query describing what the customer is looking for.
               Example: "paket foto wedding outdoor"
        tenant_id: The tenant UUID (provided in system context, do not ask customer).

    Returns:
        Formatted text listing matching products/services with name, description, and price.
        Returns "Tidak ditemukan produk yang cocok" if no results.
    """
    from app.services.embedding import EmbeddingService

    logger.info(
        "Tool search_catalog called",
        tenant_id=tenant_id,
        query=query[:100],
    )

    service = EmbeddingService()
    results = await service.search_products(
        tenant_id=tenant_id,
        query=query,
        limit=5,
    )

    if not results:
        return "Tidak ditemukan produk atau layanan yang cocok dengan pencarian."

    return EmbeddingService.format_search_results(results)


@tool
async def check_pricing_rules(
    tenant_id: str,
    product_name: str,
    requested_discount_percent: float,
) -> str:
    """Check if a requested discount is within the tenant's allowed pricing rules.

    Use this tool when:
    - Customer is negotiating price
    - Customer asks for a discount
    - You need to verify if a specific discount can be offered

    Args:
        tenant_id: The tenant UUID.
        product_name: Name of the product/service being negotiated.
        requested_discount_percent: The discount percentage requested (0-100).

    Returns:
        JSON string with: {"allowed": true/false, "max_discount_percent": 10, "reason": "..."}
    """
    logger.info(
        "Tool check_pricing_rules called",
        tenant_id=tenant_id,
        product_name=product_name[:50],
        requested_discount=requested_discount_percent,
    )

    # For MVP: hardcoded max 10% discount
    # TODO: load from tenant-specific pricing_rules table
    MAX_DISCOUNT = 10.0

    if requested_discount_percent <= MAX_DISCOUNT:
        return json.dumps(
            {
                "allowed": True,
                "max_discount_percent": MAX_DISCOUNT,
                "applied_discount": requested_discount_percent,
                "reason": f"Diskon {requested_discount_percent}% disetujui.",
            },
            ensure_ascii=False,
        )
    else:
        return json.dumps(
            {
                "allowed": False,
                "max_discount_percent": MAX_DISCOUNT,
                "applied_discount": 0,
                "reason": f"Maaf, diskon maksimal yang bisa diberikan adalah {MAX_DISCOUNT}%.",
            },
            ensure_ascii=False,
        )


@tool
async def save_lead_info(
    tenant_id: str,
    customer_phone: str,
    customer_name: str | None = None,
    notes: str | None = None,
    estimated_value: float | None = None,
) -> str:
    """Save or update lead information when customer shares contact details or shows purchase intent.

    Use this tool when:
    - Customer provides their name
    - Customer shows strong interest in a product/service
    - You have enough information to create a lead record
    - Customer provides additional contact details

    Args:
        tenant_id: The tenant UUID.
        customer_phone: Customer's WhatsApp phone number.
        customer_name: Customer's name if provided.
        notes: Any relevant notes about the lead (interest, preferences).
        estimated_value: Estimated deal value in IDR if determinable.

    Returns:
        Confirmation message with lead ID.
    """
    from app.db.session import async_session_factory
    from app.services.lead import LeadService
    from app.schemas.lead import LeadCreate

    logger.info(
        "Tool save_lead_info called",
        tenant_id=tenant_id,
        customer_phone=customer_phone,
        customer_name=customer_name,
        estimated_value=estimated_value,
    )

    async with async_session_factory() as db:
        service = LeadService(db=db)
        lead = await service.create(
            tenant_id=tenant_id,
            data=LeadCreate(
                customer_phone=customer_phone,
                customer_name=customer_name,
                notes=notes,
                estimated_value=estimated_value,
            ),
        )
        await db.commit()

    return f"Data Kakak sudah kami simpan (Lead ID: {str(lead.id)[:8]}). Tim kami akan menghubungi Kakak segera jika ada yang perlu dikonfirmasi."


def get_tools() -> list:
    """Return all available tools for the conversation agent.

    Returns:
        List of tool functions bound to the LangChain LLM.
    """
    return [search_catalog, check_pricing_rules, save_lead_info]
