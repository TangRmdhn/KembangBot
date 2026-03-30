"""Shared fixtures for agent tests."""

import pytest
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture
def sample_stage_config() -> dict:
    """A realistic stage config for a photography service tenant."""
    return {
        "stages": {
            "greeting": {
                "agent_name": "Sari",
                "business_name": "Beautiful Moments Photography",
                "brand_voice": "ramah, hangat, dan profesional",
                "goal": "Menyapa customer dan memulai percakapan",
                "instructions": "Sapa customer dengan ramah, tanyakan apa yang bisa dibantu.",
                "required_fields": [],
                "next_stage": "needs_check",
                "fallback_stage": None,
            },
            "needs_check": {
                "agent_name": "Sari",
                "business_name": "Beautiful Moments Photography",
                "brand_voice": "ramah, hangat, dan profesional",
                "goal": "Mengumpulkan informasi kebutuhan customer untuk event fotografi",
                "instructions": (
                    "Tanyakan detail kebutuhan customer: jenis event, tanggal, lokasi, "
                    "dan jumlah tamu. Arahkan percakapan secara natural."
                ),
                "required_fields": ["event_type", "date", "location", "guest_count"],
                "next_stage": "offer_paket",
                "fallback_stage": "greeting",
            },
            "offer_paket": {
                "agent_name": "Sari",
                "business_name": "Beautiful Moments Photography",
                "brand_voice": "ramah, hangat, dan profesional",
                "goal": "Menawarkan paket fotografi yang sesuai dengan kebutuhan customer",
                "instructions": (
                    "Berdasarkan informasi yang sudah dikumpulkan, rekomendasikan paket "
                    "yang paling cocok. Jelaskan fitur dan harga dengan jelas."
                ),
                "required_fields": ["package_selection"],
                "next_stage": "negotiation",
                "fallback_stage": "needs_check",
            },
            "negotiation": {
                "agent_name": "Sari",
                "business_name": "Beautiful Moments Photography",
                "brand_voice": "ramah, hangat, dan profesional",
                "goal": "Menangani negosiasi harga atau diskon dari customer",
                "instructions": (
                    "Dengarkan permintaan customer, cek pricing rules, dan berikan "
                    "penawaran yang sesuai. Jangan langsung menolak, tapi jangan juga "
                    "memberikan diskon di luar batas yang diperbolehkan."
                ),
                "required_fields": ["final_price_agreement"],
                "next_stage": "booking",
                "fallback_stage": "offer_paket",
            },
            "booking": {
                "agent_name": "Sari",
                "business_name": "Beautiful Moments Photography",
                "brand_voice": "ramah, hangat, dan profesional",
                "goal": "Menutup penjualan dan melakukan booking",
                "instructions": (
                    "Konfirmasi semua detail, berikan informasi pembayaran, dan pastikan "
                    "customer melakukan booking dengan membayar DP."
                ),
                "required_fields": ["payment_method", "dp_paid"],
                "next_stage": "done",
                "fallback_stage": "negotiation",
            },
            "done": {
                "agent_name": "Sari",
                "business_name": "Beautiful Moments Photography",
                "brand_voice": "ramah, hangat, dan profesional",
                "goal": "Percakapan selesai dengan booking berhasil",
                "instructions": "Ucapkan terima kasih dan konfirmasi booking.",
                "required_fields": [],
                "next_stage": None,
                "fallback_stage": None,
            },
        },
        "initial_stage": "greeting",
    }


@pytest.fixture
def sample_state(sample_stage_config) -> dict:
    """A ConversationState dict at the needs_check stage with some fields collected."""
    return {
        "tenant_id": "test-tenant-uuid-123",
        "customer_phone": "6281234567890@c.us",
        "current_stage": "needs_check",
        "collected_fields": {"event_type": "wedding"},
        "missing_fields": ["date", "location", "guest_count"],
        "chat_history": [
            HumanMessage(content="Halo, saya mau tanya tentang jasa fotografi"),
            AIMessage(
                content="Halo! Selamat siang Kak 😊 Saya Sari dari Beautiful Moments Photography. "
                "Ada yang bisa saya bantu untuk kebutuhan fotografi Kakak?"
            ),
        ],
        "stage_config": sample_stage_config,
        "agent_output": "",
        "formatted_output": "",
        "needs_human_handoff": False,
        "handoff_reason": "",
    }


@pytest.fixture
def completed_stage_state(sample_stage_config) -> dict:
    """A state where all required fields are collected (stage should transition)."""
    return {
        "tenant_id": "test-tenant-uuid-123",
        "customer_phone": "6281234567890@c.us",
        "current_stage": "needs_check",
        "collected_fields": {
            "event_type": "wedding",
            "date": "10 Mei 2026",
            "location": "Jakarta Selatan",
            "guest_count": "200",
        },
        "missing_fields": [],
        "chat_history": [
            HumanMessage(content="Halo, saya mau tanya tentang jasa fotografi"),
            AIMessage(
                content="Halo! Selamat siang Kak 😊 Saya Sari dari Beautiful Moments Photography. "
                "Ada yang bisa saya bantu untuk kebutuhan fotografi Kakak?"
            ),
        ],
        "stage_config": sample_stage_config,
        "agent_output": "",
        "formatted_output": "",
        "needs_human_handoff": False,
        "handoff_reason": "",
    }
