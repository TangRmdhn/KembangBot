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
async def search_knowledge_base(query: str, tenant_id: str) -> str:
    """Search tenant knowledge base for FAQ, policies, and business information.

    Use this tool when:
    - Customer asks about store policies (return, warranty, etc)
    - Customer asks FAQ questions not in product catalog
    - Customer needs information about how the service works
    - Questions that need answers based on tenant business documents

    DO NOT use for finding products/prices — use search_catalog instead.

    Args:
        query: Customer question in natural language.
        tenant_id: Tenant UUID (from system context, don't ask customer).

    Returns:
        Relevant information from tenant knowledge base, or message if not found.
    """
    from app.db.session import async_session_factory
    from app.services.document import DocumentService

    logger.info("Tool search_knowledge_base called", tenant_id=tenant_id, query=query[:80])

    async with async_session_factory() as db:
        service = DocumentService(db=db)
        results = await service.search_knowledge_base(
            tenant_id=tenant_id,
            query=query,
            limit=4,
        )

    if not results:
        return "Tidak ditemukan informasi yang relevan di knowledge base kami."

    formatted = []
    for r in results:
        source = r.get("source", "")
        content = r.get("content", "")
        source_label = f" (dari: {source})" if source else ""
        formatted.append(f"{content}{source_label}")

    return "\n\n---\n\n".join(formatted)


@tool
async def save_lead_info(
    tenant_id: str,
    customer_phone: str,
    customer_name: str | None = None,
    notes: str | None = None,
    estimated_value: float | None = None,
) -> str:
    """Simpan informasi lead ketika customer memberikan data kontak atau menunjukkan minat beli.

    Gunakan tool ini ketika:
    - Customer menyebut namanya
    - Customer menunjukkan minat kuat terhadap produk/layanan
    - Customer memberikan informasi kontak tambahan

    Args:
        tenant_id: UUID tenant (dari system context).
        customer_phone: Nomor WhatsApp customer.
        customer_name: Nama customer jika disebutkan.
        notes: Catatan tentang kebutuhan atau preferensi customer.
        estimated_value: Estimasi nilai deal dalam IDR jika bisa ditentukan.

    Returns:
        Konfirmasi bahwa data sudah dicatat.
    """
    logger.info(
        "Tool save_lead_info called",
        tenant_id=tenant_id,
        customer_phone=customer_phone,
        customer_name=customer_name,
    )

    # Tidak simpan ke DB di sini — kembalikan data untuk disimpan
    # oleh webhook handler dalam transaction yang sama
    return json.dumps({
        "__lead_data__": True,  # marker untuk webhook handler
        "tenant_id": tenant_id,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "notes": notes,
        "estimated_value": estimated_value,
    })


def get_tools() -> list:
    """Return all available tools for the conversation agent.

    Returns:
        List of tool functions bound to the LangChain LLM.
    """
    return [search_catalog, search_knowledge_base, check_pricing_rules, save_lead_info]
