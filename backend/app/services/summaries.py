"""Cached legal and layman document summaries."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..core.generation import AnswerGenerator, SummaryStyle, summarize_document
from ..models import Document, Organization
from ..schemas import DocumentSummaryText


async def generate_summary(
    session: AsyncSession,
    settings: Settings,
    document_id: UUID,
    *,
    style: SummaryStyle,
    refresh: bool,
    generator: AnswerGenerator,
) -> DocumentSummaryText | None:
    """Return a cached summary or generate one from the document's anonymized text."""
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

    cached = (document.summaries or {}).get(style.value)
    if cached and not refresh:
        return DocumentSummaryText(
            document_id=document.id,
            style=style,
            summary=cached["text"],
            provider=cached["provider"],
            model=cached["model"],
            generated_at=datetime.fromisoformat(cached["generated_at"]),
            cached=True,
        )

    text = await asyncio.to_thread(
        Path(document.anonymized_text_path).read_text, encoding="utf-8"
    )
    generated = await summarize_document(
        text, style, generator, document_id=document.id
    )
    generated_at = datetime.now(timezone.utc)
    document.summaries = {
        **(document.summaries or {}),
        style.value: {
            "text": generated.answer,
            "provider": generated.provider,
            "model": generated.model,
            "generated_at": generated_at.isoformat(),
        },
    }
    await session.flush()
    return DocumentSummaryText(
        document_id=document.id,
        style=style,
        summary=generated.answer,
        provider=generated.provider,
        model=generated.model,
        generated_at=generated_at,
        cached=False,
    )
