"""Retrieval-augmented query endpoint."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_session
from ...core.auth import current_user
from ...models import User
from ...schemas import Citation, QueryRequest, QueryResponse
from ...services.query import answer_question
from ...services.settings import effective_settings
from ...core.generation import LLMGenerator

router = APIRouter(tags=["query"])

_EXCERPT_LENGTH = 320


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    payload: QueryRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User | None, Depends(current_user)],
) -> QueryResponse:
    if payload.reveal_pii and (user is None or user.role.value not in {"admin", "analyst"}):
        raise HTTPException(status_code=403, detail="Analyst or admin role required to reveal PII")
    try:
        effective = await effective_settings(session, request.app.state.settings)
        generator = request.app.state.generator
        if isinstance(generator, LLMGenerator):
            generator = LLMGenerator(effective)
        result = await answer_question(
            session,
            effective,
            question=payload.question,
            document_id=payload.document_id,
            limit=payload.limit,
            retriever=request.app.state.retriever,
            generator=generator,
            reveal_pii=payload.reveal_pii,
            user=user,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="The language model provider is unavailable"
        ) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return QueryResponse(
        answer=result.answer,
        provider=result.provider,
        model=result.model,
        citations=[
            Citation(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=result.filenames.get(chunk.document_id, "unknown"),
                chunk_index=chunk.chunk_index,
                score=chunk.score,
                excerpt=chunk.text[:_EXCERPT_LENGTH],
            )
            for chunk in result.chunks
        ],
    )
