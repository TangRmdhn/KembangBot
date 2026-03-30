"""Embedding pipeline for product catalog semantic search.

Manages product catalog embeddings in pgvector: embed new products,
search by semantic similarity, and delete embeddings.
"""

import asyncio
from loguru import logger

from langchain_core.documents import Document

from app.db.vector_store import get_vector_store
from app.core.exceptions import CatalogUploadError


class EmbeddingService:
    """Manages product catalog embeddings in pgvector.

    Handles the full lifecycle: embed new products, update existing embeddings,
    delete embeddings when products are removed, and search by semantic similarity.
    """

    async def embed_products(
        self,
        tenant_id: str,
        products: list[dict],
    ) -> int:
        """Embed a list of products into the tenant's pgvector collection.

        Each product dict should have at least: name, description, price, category.
        Additional fields are stored as metadata.

        Args:
            tenant_id: The tenant UUID.
            products: List of product dicts from CSV parsing.

        Returns:
            Number of products successfully embedded.

        The embedding text for each product is formatted as:
            "{name}. {description}. Kategori: {category}. Harga: Rp {price}"

        This format is optimized for Indonesian language similarity search.
        """
        try:
            store = get_vector_store(tenant_id)

            # Convert each product dict to a LangChain Document
            documents = []
            for product in products:
                # Build searchable text content
                content_parts = [product.get("name", "")]
                if product.get("description"):
                    content_parts.append(product["description"])
                if product.get("category"):
                    content_parts.append(f"Kategori: {product['category']}")
                if product.get("price"):
                    content_parts.append(f"Harga: Rp {product['price']:,.0f}")

                doc = Document(
                    page_content=". ".join(content_parts),
                    metadata={
                        "tenant_id": tenant_id,
                        "product_name": product.get("name", ""),
                        "price": product.get("price"),
                        "category": product.get("category", ""),
                        "product_id": str(product.get("id", "")),
                    },
                )
                documents.append(doc)

            if not documents:
                return 0

            # Add documents to vector store (sync call, wrap in asyncio.to_thread)
            await asyncio.to_thread(store.add_documents, documents)

            logger.info(
                "Products embedded",
                tenant_id=tenant_id,
                count=len(documents),
            )

            return len(documents)

        except Exception as e:
            logger.error(
                "Embedding failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise CatalogUploadError(f"Embedding failed: {str(e)}")

    async def search_products(
        self,
        tenant_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        """Search tenant's product catalog by semantic similarity.

        Args:
            tenant_id: The tenant UUID.
            query: Natural language search query (e.g., "paket foto wedding outdoor").
            limit: Maximum number of results to return.

        Returns:
            List of dicts with: name, description, price, category, relevance_score.
        """
        try:
            store = get_vector_store(tenant_id)

            # Search with MMR (Maximal Marginal Relevance) for diverse results
            results = await asyncio.to_thread(
                store.similarity_search_with_relevance_scores,
                query,
                k=limit,
            )

            formatted = [
                {
                    "name": doc.metadata.get("product_name", ""),
                    "price": doc.metadata.get("price"),
                    "category": doc.metadata.get("category", ""),
                    "description": doc.page_content,
                    "relevance_score": score,
                }
                for doc, score in results
            ]

            logger.info(
                "Catalog search",
                tenant_id=tenant_id,
                query=query[:50],
                results_count=len(formatted),
            )

            return formatted

        except Exception as e:
            logger.error(
                "Catalog search failed",
                tenant_id=tenant_id,
                query=query[:50],
                error=str(e),
            )
            return []

    async def delete_tenant_embeddings(self, tenant_id: str) -> None:
        """Delete ALL embeddings for a tenant.

        Used when re-uploading catalog to replace all products.

        Args:
            tenant_id: The tenant UUID.
        """
        try:
            store = get_vector_store(tenant_id)
            await asyncio.to_thread(store.delete_collection)

            logger.info(
                "Tenant embeddings deleted",
                tenant_id=tenant_id,
            )

        except Exception as e:
            logger.error(
                "Delete embeddings failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            # Don't raise - this is a cleanup operation

    @staticmethod
    def format_search_results(results: list[dict]) -> str:
        """Format search results as natural text for the AI agent.

        Args:
            results: List of search result dicts.

        Returns:
            Formatted string with numbered list of products.

        Example output:
            1. Paket Wedding Gold — Rp 5.000.000
               Foto unlimited, 1 album, 1 videografer
            2. Paket Prewedding — Rp 2.500.000
               3 lokasi, 50 foto edit, cetak 10R
        """
        if not results:
            return "Maaf, tidak ditemukan produk atau layanan yang cocok dengan pencarian."

        formatted = []
        for i, result in enumerate(results, 1):
            name = result.get("name", "Unknown")
            price = result.get("price")
            description = result.get("description", "")

            # Extract just the description part (after name)
            desc_parts = description.split(". ", 1)
            short_desc = desc_parts[1] if len(desc_parts) > 1 else ""

            if price:
                formatted.append(f"{i}. {name} — Rp {price:,.0f}")
            else:
                formatted.append(f"{i}. {name}")

            if short_desc:
                formatted.append(f"   {short_desc}")

        return "\n".join(formatted)
