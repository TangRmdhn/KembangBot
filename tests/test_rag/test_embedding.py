"""Tests for embedding service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_embed_products_creates_documents(sample_products, mock_vector_store):
    """Test embed_products creates Document objects correctly."""
    with patch("app.services.embedding.get_vector_store", return_value=mock_vector_store):
        service = EmbeddingService()
        count = await service.embed_products("tenant-123", sample_products)

        assert mock_vector_store.add_documents.called
        docs = mock_vector_store.add_documents.call_args[0][0]
        assert len(docs) == 3
        assert "Paket Wedding Gold" in docs[0].page_content


@pytest.mark.asyncio
async def test_embed_products_formats_content_correctly(sample_products, mock_vector_store):
    """Test document page_content includes name, description, category, price."""
    with patch("app.services.embedding.get_vector_store", return_value=mock_vector_store):
        service = EmbeddingService()
        await service.embed_products("tenant-123", sample_products)

        docs = mock_vector_store.add_documents.call_args[0][0]
        content = docs[0].page_content
        assert "Paket Wedding Gold" in content
        assert "Full day, 2 fotografer" in content
        assert "Kategori: Wedding" in content
        assert "Harga: Rp 8,500,000" in content


@pytest.mark.asyncio
async def test_search_products_returns_results(mock_vector_store):
    """Test search_products returns formatted results."""
    from langchain_core.documents import Document

    mock_doc = Document(
        page_content="Test product. Description. Kategori: Test. Harga: Rp 1000",
        metadata={
            "product_name": "Test Product",
            "price": 1000,
            "category": "Test",
        },
    )
    mock_vector_store.similarity_search_with_relevance_scores.return_value = [
        (mock_doc, 0.95)
    ]

    with patch("app.services.embedding.get_vector_store", return_value=mock_vector_store):
        service = EmbeddingService()
        results = await service.search_products("tenant-123", "test query")

        assert len(results) == 1
        assert results[0]["name"] == "Test Product"
        assert results[0]["relevance_score"] == 0.95


@pytest.mark.asyncio
async def test_search_products_empty_results(mock_vector_store):
    """Test search_products returns empty list when no results."""
    mock_vector_store.similarity_search_with_relevance_scores.return_value = []

    with patch("app.services.embedding.get_vector_store", return_value=mock_vector_store):
        service = EmbeddingService()
        results = await service.search_products("tenant-123", "no match query")

        assert results == []


def test_format_search_results_formatting():
    """Test the static formatter produces numbered list."""
    results = [
        {
            "name": "Paket A",
            "price": 1000000,
            "description": "Name. Deskripsi produk. Kategori: Test",
        },
        {
            "name": "Paket B",
            "price": 2000000,
            "description": "Name. Deskripsi lain. Kategori: Test",
        },
    ]

    formatted = EmbeddingService.format_search_results(results)

    assert "1. Paket A — Rp 1,000,000" in formatted
    assert "2. Paket B — Rp 2,000,000" in formatted


def test_format_search_results_empty():
    """Test format returns 'tidak ditemukan' message for empty results."""
    formatted = EmbeddingService.format_search_results([])
    assert "tidak ditemukan produk" in formatted


@pytest.mark.asyncio
async def test_delete_tenant_embeddings(mock_vector_store):
    """Test delete_tenant_embeddings calls delete_collection."""
    with patch("app.services.embedding.get_vector_store", return_value=mock_vector_store):
        service = EmbeddingService()
        await service.delete_tenant_embeddings("tenant-123")

        mock_vector_store.delete_collection.assert_called_once()
