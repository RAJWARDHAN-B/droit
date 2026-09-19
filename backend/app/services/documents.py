"""Transactional document ingestion services."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..config import Settings
from ..core.chunking import split_text
from ..core.embedding import ChunkVector, VectorIndexer
from ..core.ingestion import (
    SUPPORTED_EXTENSIONS,
    extract_document_metadata,
    load_document,
)
from ..core.pii import anonymize_text, encrypt_value
from ..core.risk import RiskEnricher, score_document_risk
from ..models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    Organization,
    PIIMapping,
    ProcessingJob,
    ProcessingStage,
)
from ..schemas import DocumentContent, DocumentSummary, ProcessingJobResponse

logger = logging.getLogger(__name__)


def job_response(job: ProcessingJob) -> ProcessingJobResponse:
    return ProcessingJobResponse(
        job_id=job.id,
        document_id=job.document_id,
        filename=job.document.filename,
        document_status=job.document.status,
        stage=job.stage,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def get_processing_job(
    session: AsyncSession, job_id: UUID
) -> ProcessingJob | None:
    result = await session.execute(
        select(ProcessingJob)
        .options(joinedload(ProcessingJob.document))
        .where(ProcessingJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def list_documents(
    session: AsyncSession, settings: Settings
) -> list[DocumentSummary]:
    """Return newest-first document summaries owned by the current organization."""
    result = await session.execute(
        select(Document)
        .join(Organization)
        .options(selectinload(Document.chunks))
        .where(Organization.slug == settings.default_org_id)
        .order_by(Document.created_at.desc())
    )
    return [
        DocumentSummary(
            id=document.id,
            filename=document.filename,
            media_type=document.media_type,
            status=document.status,
            created_at=document.created_at,
            chunk_count=len(document.chunks),
            character_count=document.document_metadata.get("character_count"),
            pii_count=document.document_metadata.get("pii_count"),
            risk_score=document.risk_score,
            risk_breakdown=document.risk_breakdown,
        )
        for document in result.scalars().all()
    ]


async def get_document_content(
    session: AsyncSession, settings: Settings, document_id: UUID
) -> DocumentContent | None:
    """Return organization-scoped anonymized text for the document viewer."""
    result = await session.execute(
        select(Document)
        .join(Organization)
        .where(
            Document.id == document_id,
            Organization.slug == settings.default_org_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None or document.anonymized_text_path is None:
        return None
    text = await asyncio.to_thread(
        Path(document.anonymized_text_path).read_text, encoding="utf-8"
    )
    return DocumentContent(id=document.id, filename=document.filename, text=text)


async def delete_document(
    session: AsyncSession,
    settings: Settings,
    document_id: UUID,
    *,
    vector_indexer: VectorIndexer,
) -> bool:
    """Delete an organization-owned document and all of its stored artifacts."""
    result = await session.execute(
        select(Document)
        .join(Organization)
        .options(selectinload(Document.chunks))
        .where(
            Document.id == document_id,
            Organization.slug == settings.default_org_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        return False

    point_ids = [UUID(chunk.qdrant_point_id) for chunk in document.chunks if chunk.qdrant_point_id]
    stored_paths = [
        Path(path)
        for path in (
            document.storage_path,
            document.raw_text_path,
            document.anonymized_text_path,
        )
        if path
    ]

    try:
        await vector_indexer.delete(point_ids)
        await session.delete(document)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    for path in stored_paths:
        path.unlink(missing_ok=True)
    return True


async def ingest_document(
    session: AsyncSession,
    settings: Settings,
    *,
    filename: str,
    media_type: str | None,
    content: bytes,
    idempotency_key: str | None,
    vector_indexer: VectorIndexer,
    risk_enricher: RiskEnricher | None = None,
) -> tuple[ProcessingJob, bool]:
    """Persist and extract a document, returning its durable processing job."""
    safe_filename = _safe_filename(filename)
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{suffix}'. Supported types: {supported}")
    if not content:
        raise ValueError("Document content cannot be empty")
    if len(content) > settings.max_upload_bytes:
        raise ValueError(
            f"Document exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit"
        )

    key = _idempotency_key(settings.default_org_id, content, idempotency_key)
    existing = await _find_job_by_key(session, key)
    if existing is not None:
        return existing, False

    organization = await _get_or_create_organization(session, settings.default_org_id)
    await session.flush()
    document_id = uuid4()
    original_path = settings.upload_directory / f"{document_id}_original{suffix}"
    raw_text_path = settings.upload_directory / f"{document_id}_raw_text.txt"
    anonymized_text_path = (
        settings.upload_directory / f"{document_id}_anonymized_text.txt"
    )
    point_ids: list[UUID] = []

    try:
        await asyncio.to_thread(_write_atomic, original_path, content)
        extracted_text = await asyncio.to_thread(load_document, original_path)
        document_metadata = await asyncio.to_thread(
            extract_document_metadata, original_path, extracted_text
        )
        await asyncio.to_thread(
            _write_atomic, raw_text_path, extracted_text.encode("utf-8")
        )
        anonymized_text, pii_matches = await asyncio.to_thread(
            anonymize_text, extracted_text
        )
        pii_density = len(pii_matches) / max(len(extracted_text), 1)
        risk_assessment = await asyncio.to_thread(
            score_document_risk,
            anonymized_text,
            pii_density=pii_density,
        )
        if risk_enricher is not None and settings.llm_api_key is not None:
            try:
                risk_assessment = await risk_enricher.enrich(
                    anonymized_text, risk_assessment
                )
            except Exception:
                logger.warning(
                    "LLM risk enrichment failed; retaining heuristic assessment",
                    exc_info=True,
                )
        await asyncio.to_thread(
            _write_atomic, anonymized_text_path, anonymized_text.encode("utf-8")
        )

        document = Document(
            id=document_id,
            organization=organization,
            filename=safe_filename,
            media_type=media_type,
            storage_path=str(original_path),
            raw_text_path=str(raw_text_path),
            anonymized_text_path=str(anonymized_text_path),
            status=DocumentStatus.PROCESSING,
            document_metadata={
                **document_metadata,
                "pii_count": len(pii_matches),
                "pii_density": pii_density,
            },
            risk_score=risk_assessment.score,
            risk_breakdown=risk_assessment.breakdown,
        )
        document.pii_mappings.extend(
            PIIMapping(
                alias=match.alias,
                entity_type=match.entity_type,
                original_value_encrypted=encrypt_value(match.original_value, settings),
            )
            for match in pii_matches
        )
        chunk_texts = split_text(
            anonymized_text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunk_vectors = [
            ChunkVector(point_id=uuid4(), chunk_index=index, text=chunk_text)
            for index, chunk_text in enumerate(chunk_texts)
        ]
        point_ids = [chunk.point_id for chunk in chunk_vectors]
        await vector_indexer.index(
            document_id=document_id,
            organization_id=organization.id,
            chunks=chunk_vectors,
        )
        document.chunks.extend(
            DocumentChunk(
                id=chunk.point_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                qdrant_point_id=str(chunk.point_id),
                chunk_metadata={"filename": safe_filename},
            )
            for chunk in chunk_vectors
        )
        job = ProcessingJob(
            document=document,
            idempotency_key=key,
            stage=ProcessingStage.DONE,
        )
        document.status = DocumentStatus.READY
        session.add(job)
        await session.commit()
        return job, True
    except Exception:
        await session.rollback()
        if point_ids:
            await vector_indexer.delete(point_ids)
        original_path.unlink(missing_ok=True)
        raw_text_path.unlink(missing_ok=True)
        anonymized_text_path.unlink(missing_ok=True)
        raise


async def _find_job_by_key(
    session: AsyncSession, idempotency_key: str
) -> ProcessingJob | None:
    result = await session.execute(
        select(ProcessingJob)
        .options(joinedload(ProcessingJob.document))
        .where(ProcessingJob.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def _get_or_create_organization(
    session: AsyncSession, slug: str
) -> Organization:
    result = await session.execute(select(Organization).where(Organization.slug == slug))
    organization = result.scalar_one_or_none()
    if organization is None:
        organization = Organization(slug=slug, name="Default Organization")
        session.add(organization)
    return organization


def _safe_filename(filename: str) -> str:
    safe_name = Path(filename).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("A valid filename is required")
    if len(safe_name) > 255:
        raise ValueError("Filename cannot exceed 255 characters")
    return safe_name


def _idempotency_key(org_slug: str, content: bytes, supplied_key: str | None) -> str:
    value = supplied_key.strip() if supplied_key else hashlib.sha256(content).hexdigest()
    if not value:
        raise ValueError("Idempotency-Key cannot be blank")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{org_slug}:{digest}"


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp-{uuid4().hex}")
    try:
        temporary_path.write_bytes(content)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)