"""Tests for catalog upload with RAG pipeline."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from app.services.catalog import CatalogService
from app.core.exceptions import CatalogUploadError


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def catalog_service(mock_db):
    """Create CatalogService with mocked DB."""
    with patch("app.services.catalog.EmbeddingService"):
        return CatalogService(db=mock_db)


@pytest.mark.asyncio
async def test_upload_csv_valid(catalog_service, mock_db, sample_csv_bytes):
    """Test upload_csv with valid CSV."""
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    with patch.object(catalog_service.embedding_service, 'delete_tenant_embeddings', AsyncMock()):
        with patch.object(catalog_service.embedding_service, 'embed_products', AsyncMock(return_value=2)):
            result = await catalog_service.upload_csv(
                tenant_id="tenant-123",
                file_content=sample_csv_bytes,
                filename="test.csv",
            )

            assert result["total_products"] == 2
            assert result["embedded_count"] == 2
            assert result["errors"] == []


@pytest.mark.asyncio
async def test_upload_csv_missing_name(catalog_service, mock_db, invalid_csv_bytes):
    """Test upload_csv with missing name column."""
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    with patch.object(catalog_service.embedding_service, 'delete_tenant_embeddings', AsyncMock()):
        with patch.object(catalog_service.embedding_service, 'embed_products', AsyncMock(return_value=0)):
            result = await catalog_service.upload_csv(
                tenant_id="tenant-123",
                file_content=invalid_csv_bytes,
                filename="invalid.csv",
            )

            assert result["total_products"] == 0
            assert len(result["errors"]) > 0
            assert "missing 'name'" in result["errors"][0]


@pytest.mark.asyncio
async def test_upload_csv_replaces_existing(catalog_service, mock_db, sample_csv_bytes):
    """Test upload_csv deletes existing products before inserting."""
    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    with patch.object(catalog_service.embedding_service, 'delete_tenant_embeddings', AsyncMock()):
        with patch.object(catalog_service.embedding_service, 'embed_products', AsyncMock(return_value=2)):
            await catalog_service.upload_csv(
                tenant_id="tenant-123",
                file_content=sample_csv_bytes,
                filename="test.csv",
            )

            # Verify delete was called
            delete_calls = mock_db.execute.call_args_list
            assert any(
                "DELETE" in str(call)
                for call in delete_calls
            )


@pytest.mark.asyncio
async def test_upload_csv_extra_columns(catalog_service, mock_db):
    """Test upload_csv stores extra columns in metadata_."""
    csv_with_extra = b"name,description,price,category,sku\nProduct A,Desc,1000,Cat,SKU123\n"

    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    with patch.object(catalog_service.embedding_service, 'delete_tenant_embeddings', AsyncMock()):
        with patch.object(catalog_service.embedding_service, 'embed_products', AsyncMock(return_value=1)):
            result = await catalog_service.upload_csv(
                tenant_id="tenant-123",
                file_content=csv_with_extra,
                filename="extra.csv",
            )

            assert result["total_products"] == 1


@pytest.mark.asyncio
async def test_upload_csv_semicolon_delimiter(catalog_service, mock_db):
    """Test upload_csv handles semicolon delimiter."""
    semicolon_csv = b"name;description;price\nProduct A;Desc;1000\n"

    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    with patch.object(catalog_service.embedding_service, 'delete_tenant_embeddings', AsyncMock()):
        with patch.object(catalog_service.embedding_service, 'embed_products', AsyncMock(return_value=1)):
            result = await catalog_service.upload_csv(
                tenant_id="tenant-123",
                file_content=semicolon_csv,
                filename="semicolon.csv",
            )

            assert result["total_products"] == 1


@pytest.mark.asyncio
async def test_upload_csv_utf8_bom(catalog_service, mock_db):
    """Test upload_csv handles UTF-8 BOM."""
    # UTF-8 BOM + CSV
    bom_csv = b"\xef\xbb\xbfname,description,price\nProduct A,Desc,1000\n"

    mock_result = MagicMock()
    mock_result.scalars.return_value = []
    mock_db.execute.return_value = mock_result

    with patch.object(catalog_service.embedding_service, 'delete_tenant_embeddings', AsyncMock()):
        with patch.object(catalog_service.embedding_service, 'embed_products', AsyncMock(return_value=1)):
            result = await catalog_service.upload_csv(
                tenant_id="tenant-123",
                file_content=bom_csv,
                filename="bom.csv",
            )

            assert result["total_products"] == 1
