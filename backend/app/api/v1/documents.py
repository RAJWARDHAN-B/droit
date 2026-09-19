"""Document ingestion endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_session
from ...schemas import (
    DocumentContent,
    DocumentSummary,
    PasteDocumentRequest,
    ProcessingJobResponse,
)
from ...services.documents import (
    delete_document,
    get_processing_job,
    ingest_document,
    get_document_content,
    job_response,
    list_documents,
)

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentSummary])
async def list_all_documents(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[DocumentSummary]:
    return await list_documents(session, request.app.state.settings)


@router.post("/documents/upload", response_model=ProcessingJobResponse, status_code=201)
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ProcessingJobResponse:
    try:
        content = await file.read(request.app.state.settings.max_upload_bytes + 1)
        job, created = await ingest_document(
            session,
            request.app.state.settings,
            filename=file.filename or "",
            media_type=file.content_type,
            content=content,
            idempotency_key=idempotency_key,
            vector_indexer=request.app.state.vector_indexer,
            risk_enricher=request.app.state.risk_enricher,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()

    if not created:
        response.status_code = 200
    return job_response(job)


@router.post("/documents/paste", response_model=ProcessingJobResponse, status_code=201)
async def paste_document(
    payload: PasteDocumentRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ProcessingJobResponse:
    filename = payload.title if payload.title.lower().endswith(".txt") else f"{payload.title}.txt"
    try:
        job, created = await ingest_document(
            session,
            request.app.state.settings,
            filename=filename,
            media_type="text/plain",
            content=payload.text.encode("utf-8"),
            idempotency_key=idempotency_key,
            vector_indexer=request.app.state.vector_indexer,
            risk_enricher=request.app.state.risk_enricher,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not created:
        response.status_code = 200
    return job_response(job)


@router.get("/documents/{document_id}/content", response_model=DocumentContent)
async def document_content(
    document_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentContent:
    content = await get_document_content(
        session, request.app.state.settings, document_id
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Document content not found")
    return content


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
async def processing_job(
    job_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProcessingJobResponse:
    job = await get_processing_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return job_response(job)


@router.delete("/documents/{document_id}", status_code=204)
async def remove_document(
    document_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    deleted = await delete_document(
        session,
        request.app.state.settings,
        document_id,
        vector_indexer=request.app.state.vector_indexer,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(status_code=204)