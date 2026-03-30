"""Abstract base model for Kembang AI ORM models.

All models inherit from Base which provides common fields:
- id: UUID primary key
- created_at: timestamp of creation
- updated_at: timestamp of last update
"""

from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    """Abstract base class for all ORM models.

    Provides common fields and configuration for all models.
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
