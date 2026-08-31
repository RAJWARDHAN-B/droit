"""Transactional document ingestion services."""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..config import Settings
from ..core.ingestion import SUPPORTED_EXTENSIONS, load_document
from ..models import (
    Document,
    DocumentStatus,
    Organization,
    ProcessingJob,
    ProcessingStage,
)
from ..schemas import ProcessingJobResponse


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


async def ingest_document(
    session: AsyncSession,
    settings: Settings,
    *,
    filename: str,
    media_type: str | None,
    content: bytes,
    idempotency_key: str | None,
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
    document_id = uuid4()
    original_path = settings.upload_directory / f"{document_id}_original{suffix}"
    raw_text_path = settings.upload_directory / f"{document_id}_raw_text.txt"

    try:
        await asyncio.to_thread(_write_atomic, original_path, content)
        extracted_text = await asyncio.to_thread(load_document, original_path)
        await asyncio.to_thread(
            _write_atomic, raw_text_path, extracted_text.encode("utf-8")
        )

        document = Document(
            id=document_id,
            organization=organization,
            filename=safe_filename,
            media_type=media_type,
            storage_path=str(original_path),
            raw_text_path=str(raw_text_path),
            status=DocumentStatus.PROCESSING,
            document_metadata={"character_count": len(extracted_text)},
        )
        job = ProcessingJob(
            document=document,
            idempotency_key=key,
            stage=ProcessingStage.PII_SCAN,
        )
        session.add(job)
        await session.commit()
        return job, True
    except Exception:
        await session.rollback()
        original_path.unlink(missing_ok=True)
        raw_text_path.unlink(missing_ok=True)
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