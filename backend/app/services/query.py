"""Retrieval-augmented question answering over indexed documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..core.generation import AnswerGenerator
from ..core.pii import decrypt_value, restore_text
from ..core.retrieval import HybridRetriever, RetrievedChunk
from ..models import Document, Organization, PIIMapping

NO_CONTEXT_ANSWER = (
    "No indexed content is available to answer this question. "
    "Upload a document and wait for processing to finish."
)


@dataclass(frozen=True)
class QueryResult:
    answer: str
    provider: str
    model: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    filenames: dict[UUID, str] = field(default_factory=dict)


async def answer_question(
    session: AsyncSession,
    settings: Settings,
    *,
    question: str,
    document_id: UUID | None,
    limit: int,
    retriever: HybridRetriever,
    generator: AnswerGenerator,
) -> QueryResult:
    """Answer a question from anonymized context owned by the current organization."""
    if not question.strip():
        raise ValueError("Question cannot be blank")

    organization_id = await _organization_id(session, settings.default_org_id)
    chunks: list[RetrievedChunk] = []
    if organization_id is not None:
        chunks = await retriever.retrieve(
            session,
            question,
            organization_id=organization_id,
            document_id=document_id,
            limit=limit,
        )

    if not chunks:
        return QueryResult(
            answer=NO_CONTEXT_ANSWER,
            provider=settings.llm_provider,
            model=settings.llm_model,
        )

    generated = await generator.generate(question, chunks)
    replacements_by_document = await _pii_replacements(
        session, settings, {chunk.document_id for chunk in chunks}
    )
    replacements = _unambiguous_replacements(replacements_by_document)
    return QueryResult(
        answer=restore_text(generated.answer, replacements),
        provider=generated.provider,
        model=generated.model,
        chunks=[
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                text=restore_text(
                    chunk.text, replacements_by_document.get(chunk.document_id, {})
                ),
                score=chunk.score,
            )
            for chunk in chunks
        ],
        filenames=await _filenames(
            session, {chunk.document_id for chunk in chunks}
        ),
    )


async def _pii_replacements(
    session: AsyncSession, settings: Settings, document_ids: set[UUID]
) -> dict[UUID, dict[str, str]]:
    result = await session.execute(
        select(
            PIIMapping.document_id,
            PIIMapping.alias,
            PIIMapping.original_value_encrypted,
        ).where(PIIMapping.document_id.in_(document_ids))
    )
    replacements_by_document = {document_id: {} for document_id in document_ids}
    for document_id, alias, encrypted_value in result.all():
        replacements_by_document[document_id][alias] = decrypt_value(
            encrypted_value, settings
        )
    return replacements_by_document


def _unambiguous_replacements(
    replacements_by_document: dict[UUID, dict[str, str]],
) -> dict[str, str]:
    candidates: dict[str, set[str]] = {}
    for document_replacements in replacements_by_document.values():
        for alias, value in document_replacements.items():
            candidates.setdefault(alias, set()).add(value)
    return {
        alias: next(iter(values))
        for alias, values in candidates.items()
        if len(values) == 1
    }


async def _organization_id(session: AsyncSession, slug: str) -> UUID | None:
    result = await session.execute(
        select(Organization.id).where(Organization.slug == slug)
    )
    return result.scalar_one_or_none()


async def _filenames(
    session: AsyncSession, document_ids: set[UUID]
) -> dict[UUID, str]:
    result = await session.execute(
        select(Document.id, Document.filename).where(Document.id.in_(document_ids))
    )
    return {document_id: filename for document_id, filename in result.all()}
