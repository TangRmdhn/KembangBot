"""Common schemas for Kembang AI.

Shared response wrappers and pagination schemas.
"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    success: bool = True
    data: T
    message: str | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response wrapper."""

    success: bool = True
    data: list[T]
    meta: PaginationMeta


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = False
    error: str
    code: str
    detail: str | None = None
