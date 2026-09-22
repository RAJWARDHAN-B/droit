"""Persisted conversation endpoints."""

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import current_user
from ...core.generation import LLMGenerator
from ...database import get_session
from ...models import User
from ...schemas import (
    ConversationDetail,
    ConversationSummary,
    CreateConversationRequest,
    RenameConversationRequest,
    SendMessageRequest,
)
from ...services.conversations import (
    append_exchange,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    rename_conversation,
)
from ...services.settings import effective_settings

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationDetail, status_code=201)
async def start_conversation(
    payload: CreateConversationRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> ConversationDetail:
    conversation = await create_conversation(
        session,
        request.app.state.settings,
        title=payload.title,
        document_id=payload.document_id,
        user=user,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return conversation


@router.get("", response_model=list[ConversationSummary])
async def all_conversations(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> list[ConversationSummary]:
    return await list_conversations(session, request.app.state.settings, user=user)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def conversation_detail(
    conversation_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> ConversationDetail:
    conversation = await get_conversation(
        session, request.app.state.settings, conversation_id, user=user
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationSummary)
async def rename(
    conversation_id: UUID,
    payload: RenameConversationRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> ConversationSummary:
    conversation = await rename_conversation(
        session,
        request.app.state.settings,
        conversation_id,
        title=payload.title,
        user=user,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}", status_code=204)
async def remove(
    conversation_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> Response:
    deleted = await delete_conversation(
        session, request.app.state.settings, conversation_id, user=user
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return Response(status_code=204)


@router.post("/{conversation_id}/messages", response_model=ConversationDetail)
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> ConversationDetail:
    effective = await effective_settings(session, request.app.state.settings)
    generator = request.app.state.generator
    if isinstance(generator, LLMGenerator):
        generator = LLMGenerator(effective)
    try:
        conversation = await append_exchange(
            session,
            effective,
            conversation_id,
            question=payload.question,
            limit=payload.limit,
            retriever=request.app.state.retriever,
            generator=generator,
            user=user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="The language model provider is unavailable"
        ) from exc
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
