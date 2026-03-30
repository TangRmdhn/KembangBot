"""Catalog service for Kembang AI.

Handles product catalog CRUD, CSV upload, and semantic search via pgvector.
"""

import csv
import io
from decimal import Decimal
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.product import Product
from app.services.embedding import EmbeddingService
from app.core.exceptions import CatalogUploadError


class CatalogService:
    """Service for catalog operations.

    Attributes:
        db: Async SQLAlchemy session.
        embedding_service: Service for managing embeddings.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    def _parse_csv(
        self, file_content: bytes
    ) -> tuple[list[dict], list[str]]:
        """Parse CSV bytes into list of row dicts.

        Handles: UTF-8 with BOM, different delimiters (comma, semicolon, tab).

        Args:
            file_content: CSV file bytes.

        Returns:
            Tuple of (rows, errors) where rows is list of cleaned dicts.
        """
        # Decode with UTF-8-sig to handle BOM
        text = file_content.decode("utf-8-sig")

        # Detect delimiter
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(text[:2048])
        except csv.Error:
            dialect = csv.excel  # default to comma

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)

        rows = []
        errors = []
        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            # Strip whitespace from keys and values
            cleaned = {
                k.strip().lower(): v.strip()
                for k, v in row.items()
                if k
            }

            if not cleaned.get("name"):
                errors.append(f"Row {i}: missing 'name' column")
                continue

            # Parse price as float
            if cleaned.get("price"):
                try:
                    # Handle various formats: "1,000", "1.000", "1000"
                    price_str = cleaned["price"].replace(",", "").strip()
                    # Try to parse as float
                    cleaned["price"] = float(price_str)
                except ValueError:
                    errors.append(f"Row {i}: invalid price '{cleaned['price']}'")
                    cleaned["price"] = None

            rows.append(cleaned)

        return rows, errors

    async def upload_csv(
        self,
        tenant_id: str,
        file_content: bytes,
        filename: str,
    ) -> dict:
        """Parse a CSV file, create Product records, and embed them in pgvector.

        Expected CSV columns (flexible — at minimum needs 'name'):
            name (required), description, price, category

        Extra columns are stored in Product.metadata_ as JSONB.

        Flow:
        1. Parse CSV → list of dicts
        2. Validate rows (skip invalid ones, collect errors)
        3. Delete existing products for tenant (full re-upload model for MVP)
        4. Create Product records in PostgreSQL
        5. Delete existing embeddings for tenant
        6. Embed all products in pgvector
        7. Return summary with counts and errors

        Args:
            tenant_id: Tenant UUID.
            file_content: CSV file bytes.
            filename: Original filename.

        Returns:
            Dict with total_products, embedded_count, and errors list.
        """
        errors = []
        embedded_count = 0

        # Step 1: Parse CSV
        rows, parse_errors = self._parse_csv(file_content)
        errors.extend(parse_errors)

        if not rows:
            raise CatalogUploadError("No valid products found in CSV")

        logger.info(
            "CSV parsed",
            tenant_id=tenant_id,
            filename=filename,
            valid_rows=len(rows),
            errors=len(parse_errors),
        )

        # Step 2-3: Delete existing products for tenant (full re-upload)
        await self.db.execute(
            delete(Product).where(Product.tenant_id == tenant_id)
        )
        await self.db.flush()

        # Step 4: Create Product records
        product_dicts = []
        for row in rows:
            # Separate known columns from extra metadata
            known_fields = {
                "tenant_id": tenant_id,
                "name": row.get("name", ""),
                "description": row.get("description"),
                "price": Decimal(str(row["price"])) if row.get("price") else None,
                "category": row.get("category"),
            }

            # Extra columns go to metadata_
            extra_fields = {
                k: v
                for k, v in row.items()
                if k not in ["name", "description", "price", "category"]
            }
            if extra_fields:
                known_fields["metadata_"] = extra_fields

            product = Product(**known_fields)
            self.db.add(product)
            product_dicts.append(
                {
                    "id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price) if product.price else None,
                    "category": product.category,
                }
            )

        await self.db.flush()

        logger.info(
            "Products inserted",
            tenant_id=tenant_id,
            count=len(product_dicts),
        )

        # Step 5-6: Embed products
        try:
            # Delete old embeddings
            await self.embedding_service.delete_tenant_embeddings(tenant_id)

            # Embed new products
            embedded_count = await self.embedding_service.embed_products(
                tenant_id=tenant_id,
                products=product_dicts,
            )
        except Exception as e:
            logger.error(
                "Embedding failed but products saved",
                tenant_id=tenant_id,
                error=str(e),
            )
            errors.append(f"Embedding warning: {str(e)}")

        logger.info(
            "Catalog uploaded",
            tenant_id=tenant_id,
            filename=filename,
            total=len(product_dicts),
            embedded=embedded_count,
            errors=len(errors),
        )

        return {
            "total_products": len(product_dicts),
            "embedded_count": embedded_count,
            "errors": errors,
        }

    async def search(
        self, tenant_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        """Search products using semantic similarity via pgvector.

        This replaces the ILIKE stub from Layer 1.

        Args:
            tenant_id: Tenant UUID.
            query: Search query string.
            limit: Max results to return.

        Returns:
            List of matching products with relevance scores.
        """
        results = await self.embedding_service.search_products(
            tenant_id=tenant_id,
            query=query,
            limit=limit,
        )
        return results

    async def get_formatted_search_results(
        self, tenant_id: str, query: str, limit: int = 5
    ) -> str:
        """Search and return formatted text for the AI agent.

        Args:
            tenant_id: Tenant UUID.
            query: Search query.
            limit: Max results.

        Returns:
            Formatted string for AI agent response.
        """
        results = await self.search(tenant_id, query, limit)
        return EmbeddingService.format_search_results(results)

    async def list_products(
        self, tenant_id: str, page: int = 1, per_page: int = 20
    ) -> tuple[list[Product], int]:
        """List products for tenant with pagination.

        Args:
            tenant_id: Tenant UUID.
            page: Page number.
            per_page: Items per page.

        Returns:
            Tuple of (products list, total count).
        """
        offset = (page - 1) * per_page

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Product).where(
                Product.tenant_id == tenant_id
            )
        )
        total = count_result.scalar()

        # Get paginated results
        result = await self.db.execute(
            select(Product)
            .where(Product.tenant_id == tenant_id)
            .order_by(Product.name)
            .offset(offset)
            .limit(per_page)
        )
        products = result.scalars().all()

        return list(products), total

    async def delete_product(self, tenant_id: str, product_id: str) -> None:
        """Delete a product.

        Args:
            tenant_id: Tenant UUID.
            product_id: Product UUID.
        """
        await self.db.execute(
            delete(Product).where(
                Product.id == product_id,
                Product.tenant_id == tenant_id,
            )
        )
        await self.db.flush()

        # Note: For simplicity, we don't re-embed here
        # In production, you'd want to delete the specific embedding
        logger.info(
            "Product deleted",
            tenant_id=tenant_id,
            product_id=product_id,
        )
