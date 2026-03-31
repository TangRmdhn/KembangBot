"""Vector store setup for pgvector embeddings.

Provides factory functions for creating tenant-scoped PGVector instances
for product catalog semantic search.
"""

from loguru import logger
from langchain_postgres import PGVector

from app.config import settings
from app.core.model_config import embeddings as _embeddings


def get_vector_store(tenant_id: str) -> PGVector:
    """Create a tenant-scoped PGVector instance.

    Each tenant gets their own collection (namespace) in pgvector.
    This ensures complete data isolation between tenants.

    Args:
        tenant_id: UUID string of the tenant.

    Returns:
        PGVector instance scoped to the tenant's catalog collection.
    """
    logger.info(
        "Creating vector store for tenant",
        tenant_id=tenant_id,
        collection_name=f"catalog_{tenant_id}",
    )

    return PGVector(
        embeddings=_embeddings,
        collection_name=f"catalog_{tenant_id}",
        connection=settings.DATABASE_URL_SYNC,  # langchain-postgres uses sync psycopg3
        use_jsonb=True,
    )
