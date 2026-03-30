"""Shared fixtures for RAG pipeline tests."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def sample_products():
    """Sample product data for testing."""
    return [
        {
            "id": "prod-1",
            "name": "Paket Wedding Gold",
            "description": "Full day, 2 fotografer",
            "price": 8500000,
            "category": "Wedding",
        },
        {
            "id": "prod-2",
            "name": "Paket Prewedding Outdoor",
            "description": "3 lokasi outdoor",
            "price": 3500000,
            "category": "Prewedding",
        },
        {
            "id": "prod-3",
            "name": "Paket Wisuda",
            "description": "1 jam sesi foto",
            "price": 750000,
            "category": "Wisuda",
        },
    ]


@pytest.fixture
def sample_csv_bytes():
    """Valid CSV as bytes."""
    return b"name,description,price,category\nPaket Wedding Gold,Full day dokumentasi,8500000,Wedding\nPaket Prewedding,3 lokasi,3500000,Prewedding\n"


@pytest.fixture
def invalid_csv_bytes():
    """CSV with missing name column."""
    return b"description,price\nSome desc,5000\n"


@pytest.fixture
def mock_vector_store():
    """Mock PGVector store."""
    vs = MagicMock()
    vs.add_documents = MagicMock(return_value=None)
    vs.delete_collection = MagicMock()
    vs.similarity_search_with_relevance_scores = MagicMock(return_value=[])
    return vs
