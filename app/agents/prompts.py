"""Prompt template builders for Kembang AI conversation engine.

This module contains functions that compose dynamic system prompts
based on tenant configuration, current stage, and conversation state.
All prompts are in Bahasa Indonesia for Indonesian customers.
"""


def _format_fields(fields: dict) -> str:
    """Format collected fields as readable text.

    Args:
        fields: Dictionary of field names to values.

    Returns:
        Formatted string with each field on a new line, or "- (belum ada)" if empty.
    """
    if not fields:
        return "- (belum ada)"
    return "\n".join(f"- {key}: {value}" for key, value in fields.items())


def _format_missing(fields: list[str]) -> str:
    """Format missing fields as readable text.

    Args:
        fields: List of field names that are still needed.

    Returns:
        Formatted string with each field on a new line, or "- (lengkap)" if empty.
    """
    if not fields:
        return "- (lengkap)"
    return "\n".join(f"- {field}" for field in fields)


def build_system_prompt(
    agent_name: str,
    business_name: str,
    brand_voice: str,
    current_stage: str,
    stage_instructions: str,
    stage_goal: str,
    collected_fields: dict,
    missing_fields: list[str],
    tenant_id: str | None = None,
) -> str:
    """Build the complete system prompt for the conversation agent.

    This function composes a stage-specific system prompt that guides
    the AI agent's behavior based on tenant configuration and conversation state.

    Args:
        agent_name: The name the agent should use (from tenant config).
        business_name: The business/brand name.
        brand_voice: Brand voice description (e.g., "ramah dan profesional").
        current_stage: Current stage ID (e.g., "greeting", "needs_check").
        stage_instructions: Stage-specific instructions for the agent.
        stage_goal: The goal of the current stage.
        collected_fields: Data already gathered from the customer.
        missing_fields: Fields still needed before stage transition.
        tenant_id: Optional tenant UUID for tool injection.

    Returns:
        Complete system prompt in Bahasa Indonesia.
    """
    tenant_instruction = ""
    if tenant_id:
        tenant_instruction = f"\n- Saat memanggil tool, selalu gunakan tenant_id=\"{tenant_id}\"\n"

    return f"""Kamu adalah {agent_name}, AI sales assistant untuk {business_name}.

== GAYA KOMUNIKASI ==
{brand_voice}

== STAGE SAAT INI: {current_stage} ==
Tujuan stage ini: {stage_goal}

Instruksi khusus:
{stage_instructions}

== DATA YANG SUDAH TERKUMPUL ==
{_format_fields(collected_fields)}

== DATA YANG MASIH DIBUTUHKAN ==
{_format_missing(missing_fields)}

== ATURAN WAJIB ==
- Jawab dalam Bahasa Indonesia yang natural dan conversational, seperti chat biasa
- Gunakan emoji secukupnya (maksimal 2 per pesan), jangan berlebihan
- JANGAN PERNAH menyebut bahwa kamu adalah AI, bot, atau asisten virtual
- JANGAN PERNAH menyebut "stage", "field", "system", atau istilah teknis apapun
- Jika customer meminta bicara dengan manusia/owner/CS, SEGERA set needs_human_handoff=true
- Jangan memaksa customer, bangun rapport terlebih dahulu
- Arahkan percakapan secara natural ke pengumpulan data yang masih dibutuhkan
- Jika semua data sudah terkumpul, arahkan ke tahap selanjutnya secara natural
- Jika customer bertanya di luar topik, jawab singkat lalu arahkan kembali
- Jangan mengarang informasi produk/harga — HANYA gunakan data dari tool search_catalog
- Jika tidak yakin, lebih baik jujur dan tawarkan untuk menghubungkan ke tim{tenant_instruction}
"""


def build_field_extraction_prompt(
    missing_fields: list[str],
    agent_response: str,
    customer_message: str,
) -> str:
    """Build a prompt for extracting structured fields from conversation.

    This prompt is used by the supervisor to identify which missing fields
    have been answered in the latest customer message.

    Args:
        missing_fields: List of field names still needed.
        agent_response: The agent's previous response.
        customer_message: The customer's latest message.

    Returns:
        Prompt for field extraction LLM call.
    """
    missing_list = ", ".join(missing_fields) if missing_fields else "(tidak ada)"

    return f"""Analisis percakapan berikut dan ekstrak data yang diberikan customer.

Field yang masih dibutuhkan: {missing_list}

== PERCAKAPAN ==
AI: {agent_response}
Customer: {customer_message}

Tugas:
1. Identifikasi field mana dari daftar di atas yang sudah dijawab customer
2. Ekstrak nilai sebenarnya (bukan "yes"/"no"), contoh: "wedding", "10 Mei 2026", "Jakarta"
3. Kembalikan HANYA JSON object dengan field yang berhasil diekstrak
4. Jika tidak ada field yang diekstrak, kembalikan {{}}

Format output (HANYA JSON, tanpa penjelasan):
{{"field_name": "value", ...}}
"""


def build_intent_classification_prompt() -> str:
    """Build a prompt for classifying customer intent.

    Returns:
        Static prompt for intent classification LLM call.

    The output must be one of:
    - faq: customer asking a question about products/services
    - recommendation: customer wants suggestions/recommendations
    - negotiation: customer discussing price/discount/budget
    - booking: customer ready to order/book/purchase
    - followup: returning customer continuing a previous conversation
    - human_handoff: customer explicitly requests human assistance
    - chitchat: off-topic small talk
    - unknown: cannot determine intent
    """
    return """Klasifikasikan intent dari pesan customer berikut.

Pilihan intent:
- faq: customer bertanya tentang produk/layanan
- recommendation: customer minta saran/rekomendasi
- negotiation: customer membahas harga/diskon/budget
- booking: customer siap order/book/purchase
- followup: customer melanjutkan percakapan sebelumnya
- human_handoff: customer minta bicara dengan manusia/owner/CS
- chitchat: obrolan santai di luar topik
- unknown: tidak bisa menentukan intent

Kembalikan HANYA satu kata (intent), tanpa penjelasan."""
