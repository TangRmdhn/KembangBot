"""Document RAG service for tenant knowledge base.

Handles upload, chunking, embedding, and search of tenant business documents.
pgvector collection: kb_{tenant_id} (separate from catalog_{tenant_id})
"""

import asyncio
from pathlib import Path
from loguru import logger
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector

from app.models.document import TenantDocument
from app.core.model_config import embeddings
from app.config import settings


# Chunk settings — optimized for FAQ and service documents
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def get_kb_vector_store(tenant_id: str) -> PGVector:
    """Create PGVector instance for tenant knowledge base.

    Separate collection from product catalog:
    - Catalog: catalog_{tenant_id}
    - Knowledge base: kb_{tenant_id}
    """
    return PGVector(
        embeddings=embeddings,
        collection_name=f"kb_{tenant_id}",
        connection=settings.DATABASE_URL_SYNC,
        use_jsonb=True,
    )


def _chunk_text(text: str, filename: str, tenant_id: str) -> list[Document]:
    """Split text into chunks for embedding.

    Args:
        text: Document content.
        filename: Original filename for metadata.
        tenant_id: Tenant UUID for metadata.

    Returns:
        List of LangChain Documents ready for embedding.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)

    return [
        Document(
            page_content=chunk,
            metadata={
                "tenant_id": tenant_id,
                "source": filename,
                "chunk_index": i,
            },
        )
        for i, chunk in enumerate(chunks)
    ]


async def _extract_text(file_content: bytes, file_type: str) -> str:
    """Extract text from various file formats.

    Args:
        file_content: Raw file bytes.
        file_type: File extension without dot (txt, pdf, md).

    Returns:
        Extracted text.

    Raises:
        ValueError: If file format is not supported.
    """
    if file_type in ("txt", "md"):
        return file_content.decode("utf-8", errors="replace")

    elif file_type == "pdf":
        import io
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except ImportError:
            raise ValueError(
                "pypdf not installed. Add 'pypdf>=4.0.0' to pyproject.toml"
            )

    else:
        raise ValueError(f"Unsupported file format: {file_type}. Use txt, md, or pdf.")


class DocumentService:
    """Service for managing tenant knowledge base documents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload_document(
        self,
        tenant_id: str,
        file_content: bytes,
        filename: str,
    ) -> TenantDocument:
        """Upload and embed document to tenant knowledge base.

        Flow:
        1. Validate file format
        2. Extract text
        3. Save record to DB (status=pending)
        4. Chunk text
        5. Embed to pgvector
        6. Update status to embedded

        Args:
            tenant_id: Tenant UUID.
            file_content: Raw file bytes.
            filename: Original filename.

        Returns:
            Created TenantDocument record.
        """
        # Validate format
        file_type = Path(filename).suffix.lstrip(".").lower()
        if file_type not in ("txt", "md", "pdf"):
            raise ValueError(f"Unsupported format: {file_type}. Use txt, md, or pdf.")

        # Validate size (max 10MB)
        if len(file_content) > 10 * 1024 * 1024:
            raise ValueError("Maximum file size is 10MB")

        # Extract text
        text = await _extract_text(file_content, file_type)

        if not text.strip():
            raise ValueError("Document is empty or unreadable")

        # Create DB record
        doc = TenantDocument(
            tenant_id=tenant_id,
            filename=filename,
            file_type=file_type,
            content_preview=text[:500],
            status="pending",
            metadata_={"file_size_bytes": len(file_content)},
        )
        self.db.add(doc)
        await self.db.flush()

        # Chunk and embed
        try:
            chunks = _chunk_text(text, filename, tenant_id)
            store = get_kb_vector_store(tenant_id)
            await asyncio.to_thread(store.add_documents, chunks)

            doc.chunk_count = len(chunks)
            doc.status = "embedded"

            logger.info(
                "Document embedded",
                tenant_id=tenant_id,
                filename=filename,
                chunks=len(chunks),
            )

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            logger.error("Document embedding failed", tenant_id=tenant_id, error=str(e))
            raise

        await self.db.flush()
        return doc

    async def search_knowledge_base(
        self,
        tenant_id: str,
        query: str,
        limit: int = 4,
    ) -> list[dict]:
        """Search tenant knowledge base with semantic similarity.

        Args:
            tenant_id: Tenant UUID.
            query: Customer question.
            limit: Maximum results to return.

        Returns:
            List of dicts with content and score.
        """
        try:
            store = get_kb_vector_store(tenant_id)
            results = await asyncio.to_thread(
                store.similarity_search_with_relevance_scores,
                query,
                k=limit,
            )

            return [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", ""),
                    "relevance_score": score,
                }
                for doc, score in results
                if score > 0.5  # filter low relevance results
            ]

        except Exception as e:
            logger.error("KB search failed", tenant_id=tenant_id, error=str(e))
            return []

    async def list_documents(self, tenant_id: str) -> list[TenantDocument]:
        """List all tenant documents."""
        result = await self.db.execute(
            select(TenantDocument)
            .where(TenantDocument.tenant_id == tenant_id)
            .order_by(TenantDocument.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_document(self, tenant_id: str, document_id: str) -> None:
        """Delete document and its embeddings.

        Note: This deletes ALL embeddings for tenant from kb_{tenant_id}
        and re-embeds remaining documents. For MVP this is acceptable.
        TODO: Implement per-document deletion in pgvector.
        """
        # Delete from DB
        await self.db.execute(
            delete(TenantDocument).where(
                TenantDocument.id == document_id,
                TenantDocument.tenant_id == tenant_id,
            )
        )
        await self.db.flush()

        # Delete collection and re-embed remaining documents
        await self._rebuild_kb(tenant_id)

        logger.info("Document deleted", tenant_id=tenant_id, document_id=document_id)

    async def _rebuild_kb(self, tenant_id: str) -> None:
        """Rebuild knowledge base after document deletion."""
        # Delete old collection
        try:
            store = get_kb_vector_store(tenant_id)
            await asyncio.to_thread(store.delete_collection)
        except Exception:
            pass

        # Re-embed remaining documents
        result = await self.db.execute(
            select(TenantDocument).where(
                TenantDocument.tenant_id == tenant_id,
                TenantDocument.status == "embedded",
            )
        )
        docs = result.scalars().all()
        logger.info("Rebuilding KB", tenant_id=tenant_id, doc_count=len(docs))
