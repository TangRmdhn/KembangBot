"""Document model for knowledge base tenant."""

from sqlalchemy import String, ForeignKey, Index, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class TenantDocument(Base):
    """Document uploaded by tenant for knowledge base RAG.

    Attributes:
        tenant_id: Foreign key to tenant.
        filename: Original filename.
        file_type: File extension (txt, pdf, md).
        content_preview: First 500 characters for dashboard preview.
        chunk_count: Number of chunks successfully embedded.
        status: Processing status (pending, embedded, failed).
        error_message: Error message if status=failed.
        metadata_: Extra metadata (file size, etc).
    """

    __tablename__ = "tenant_documents"

    tenant_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)

    tenant: Mapped["Tenant"] = relationship(back_populates="documents")

    __table_args__ = (
        Index("ix_tenant_documents_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<TenantDocument id={self.id} file={self.filename} status={self.status}>"
