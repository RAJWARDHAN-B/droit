"""Retrieval-augmented query endpoint."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_session
from ...schemas import Citation, QueryRequest, QueryResponse
from ...services.query import answer_question

router = APIRouter(tags=["query"])

_EXCERPT_LENGTH = 320


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    payload: QueryRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> QueryResponse:
    try:
        result = await answer_question(
            session,
            request.app.state.settings,
            question=payload.question,
            document_id=payload.document_id,
            limit=payload.limit,
            retriever=request.app.state.retriever,
            generator=request.app.state.generator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="The language model provider is unavailable"
        ) from exc

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
