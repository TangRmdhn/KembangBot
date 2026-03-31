"""Document management API routes."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import APIResponse
from app.services.document import DocumentService
from app.dependencies import get_current_tenant_id
from app.db.session import get_db

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/upload", response_model=APIResponse[dict])
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Upload document to tenant knowledge base.

    Supported formats: .txt, .md, .pdf
    Maximum size: 10MB
    """
    allowed_types = {"txt", "md", "pdf"}
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_types:
        raise HTTPException(400, f"Unsupported format: {ext}. Use txt, md, or pdf.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Maximum file size is 10MB")

    service = DocumentService(db=db)
    doc = await service.upload_document(
        tenant_id=tenant_id,
        file_content=content,
        filename=file.filename,
    )

    return APIResponse(
        success=True,
        data={
            "id": str(doc.id),
            "filename": doc.filename,
            "chunks": doc.chunk_count,
            "status": doc.status,
        },
        message=f"Document uploaded and embedded ({doc.chunk_count} chunks)",
    )


@router.get("/", response_model=APIResponse[list])
async def list_documents(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list]:
    """List all tenant knowledge base documents."""
    service = DocumentService(db=db)
    docs = await service.list_documents(tenant_id)

    return APIResponse(
        success=True,
        data=[
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "chunk_count": d.chunk_count,
                "status": d.status,
                "content_preview": d.content_preview,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete document from knowledge base."""
    service = DocumentService(db=db)
    await service.delete_document(tenant_id, document_id)
