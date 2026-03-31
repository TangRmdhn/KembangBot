# Core module - cross-cutting concerns

from app.core.model_config import agent_llm, supervisor_llm, embeddings, get_model_info

__all__ = ["agent_llm", "supervisor_llm", "embeddings", "get_model_info"]
