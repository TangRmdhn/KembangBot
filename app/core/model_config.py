"""Centralized model configuration for Kembang AI.

Single source of truth for all LLM and embedding models.
To switch models, only edit this file.

Supported LLM providers:
  - OpenAI: gpt-4o-mini, gpt-4o, gpt-4-turbo
  - Anthropic: claude-3-5-haiku-20241022, claude-sonnet-4-5 (uncomment to use)
  - OpenRouter: any model via OPENROUTER_API_KEY

Supported embedding models:
  - OpenAI: text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings


# ─────────────────────────────────────────────
#  LLM — Conversation Agent
#  Used in: app/agents/conversation.py
#  Role: Generate natural responses to customers
# ─────────────────────────────────────────────
AGENT_MODEL_NAME = "gpt-4o-mini"
AGENT_TEMPERATURE = 0.7
AGENT_MAX_TOKENS = 500

agent_llm = ChatOpenAI(
    model=AGENT_MODEL_NAME,
    temperature=AGENT_TEMPERATURE,
    max_tokens=AGENT_MAX_TOKENS,
    openai_api_key=settings.OPENAI_API_KEY,
)


# ─────────────────────────────────────────────
#  LLM — Supervisor
#  Used in: app/agents/supervisor.py
#  Role: Intent classification + field extraction
#  Note: Keep temperature=0 for deterministic output
# ─────────────────────────────────────────────
SUPERVISOR_MODEL_NAME = "gpt-4o-mini"
SUPERVISOR_TEMPERATURE = 0.0
SUPERVISOR_MAX_TOKENS = 500

supervisor_llm = ChatOpenAI(
    model=SUPERVISOR_MODEL_NAME,
    temperature=SUPERVISOR_TEMPERATURE,
    max_tokens=SUPERVISOR_MAX_TOKENS,
    openai_api_key=settings.OPENAI_API_KEY,
)


# ─────────────────────────────────────────────
#  Embedding Model
#  Used in: app/db/vector_store.py, app/services/embedding.py
#  Role: Generate embeddings for product catalog + documents
# ─────────────────────────────────────────────
EMBEDDING_MODEL_NAME = "text-embedding-3-small"

embeddings = OpenAIEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    openai_api_key=settings.OPENAI_API_KEY,
)


# ─────────────────────────────────────────────
#  Model info helper — useful for logging & health check
# ─────────────────────────────────────────────
def get_model_info() -> dict:
    """Return current model config. Used by /health endpoint."""
    return {
        "agent_model": AGENT_MODEL_NAME,
        "supervisor_model": SUPERVISOR_MODEL_NAME,
        "embedding_model": EMBEDDING_MODEL_NAME,
    }
