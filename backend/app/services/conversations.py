"""Persisted conversation history over the retrieval-augmented query service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import Settings
from ..core.generation import AnswerGenerator
from ..core.retrieval import HybridRetriever
from ..models import (
    Conversation,
    ConversationMessage,
    Document,
    MessageRole,
    Organization,
    User,
)
from ..schemas import (
    Citation,
    ConversationDetail,
    ConversationMessageResponse,
    ConversationSummary,
)
from .query import answer_question
from .documents import get_or_create_organization

EXCERPT_LENGTH = 320
_TITLE_LENGTH = 60


async def create_conversation(
    session: AsyncSession,
    settings: Settings,
    *,
    title: str | None,
    document_id: UUID | None,
    user: User | None,
) -> ConversationDetail | None:
    organization = await get_or_create_organization(session, settings.default_org_id)
    await session.flush()
    if document_id is not None:
        owned = await session.scalar(
            select(Document.id).where(
                Document.id == document_id,
                Document.organization_id == organization.id,
            )
        )
        if owned is None:
            return None
    conversation = Conversation(
        organization_id=organization.id,
        user_id=user.id if user else None,
        document_id=document_id,
        title=title or "New conversation",
    )
    session.add(conversation)
    await session.flush()
    return _detail(conversation, [])


async def list_conversations(
    session: AsyncSession, settings: Settings, *, user: User | None
) -> list[ConversationSummary]:
    result = await session.execute(
        _owned_query(settings, user)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
    )
    return [
        ConversationSummary(
            id=conversation.id,
            title=conversation.title,
            document_id=conversation.document_id,
            message_count=len(conversation.messages),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation in result.scalars().all()
    ]


async def get_conversation(
    session: AsyncSession, settings: Settings, conversation_id: UUID, *, user: User | None
) -> ConversationDetail | None:
    conversation = await _load(session, settings, conversation_id, user=user)
    if conversation is None:
        return None
    return _detail(conversation, conversation.messages)


async def rename_conversation(
    session: AsyncSession,
    settings: Settings,
    conversation_id: UUID,
    *,
    title: str,
    user: User | None,
) -> ConversationSummary | None:
    conversation = await _load(session, settings, conversation_id, user=user)
    if conversation is None:
        return None
    conversation.title = title
    await session.flush()
    return _detail(conversation, conversation.messages)


async def delete_conversation(
    session: AsyncSession, settings: Settings, conversation_id: UUID, *, user: User | None
) -> bool:
    conversation = await _load(session, settings, conversation_id, user=user)
    if conversation is None:
        return False
    await session.delete(conversation)
    await session.flush()
    return True


async def append_exchange(
    session: AsyncSession,
    settings: Settings,
    conversation_id: UUID,
    *,
    question: str,
    limit: int,
    retriever: HybridRetriever,
    generator: AnswerGenerator,
    user: User | None,
) -> ConversationDetail | None:
    """Answer a question in a conversation and persist both messages with aliases intact."""
    conversation = await _load(session, settings, conversation_id, user=user)
    if conversation is None:
        return None

    result = await answer_question(
        session,
        settings,
        question=question,
        document_id=conversation.document_id,
        limit=limit,
        retriever=retriever,
        generator=generator,
        user=user,
    )
    citations = [
        {
            "chunk_id": str(chunk.chunk_id),
            "document_id": str(chunk.document_id),
            "filename": result.filenames.get(chunk.document_id, "unknown"),
            "chunk_index": chunk.chunk_index,
            "score": chunk.score,
            "excerpt": chunk.text[:EXCERPT_LENGTH],
        }
        for chunk in result.chunks
    ]
    ordinal = len(conversation.messages)
    conversation.messages.append(
        ConversationMessage(
            ordinal=ordinal, role=MessageRole.USER, content=question, citations=[]
        )
    )
    conversation.messages.append(
        ConversationMessage(
            ordinal=ordinal + 1,
            role=MessageRole.ASSISTANT,
            content=result.answer,
            citations=citations,
            provider=result.provider,
            model=result.model,
        )
    )
    if ordinal == 0:
        conversation.title = _derive_title(question)
    await session.flush()
    return _detail(conversation, conversation.messages)


def _owned_query(settings: Settings, user: User | None):
    query = select(Conversation).join(Organization).where(
        Organization.slug == settings.default_org_id
    )
    # Conversations are private to their author; anonymous sessions only see anonymous threads.
    if user is None:
        return query.where(Conversation.user_id.is_(None))
    return query.where(Conversation.user_id == user.id)


async def _load(
    session: AsyncSession, settings: Settings, conversation_id: UUID, *, user: User | None
) -> Conversation | None:
    result = await session.execute(
        _owned_query(settings, user)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


def _detail(
    conversation: Conversation, messages: list[ConversationMessage]
) -> ConversationDetail:
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        document_id=conversation.document_id,
        message_count=len(messages),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            ConversationMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                citations=[Citation(**citation) for citation in message.citations],
                provider=message.provider,
                model=message.model,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


def _derive_title(question: str) -> str:
    condensed = " ".join(question.split())
    if len(condensed) <= _TITLE_LENGTH:
        return condensed
    return f"{condensed[:_TITLE_LENGTH].rstrip()}…"
