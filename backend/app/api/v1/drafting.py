"""Protected legal drafting endpoints."""

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import required_user
from ...core.generation import LLMGenerator
from ...database import get_session
from ...models import User
from ...schemas import (
    CreateDraftRequest,
    DraftDetail,
    DraftSummary,
    DraftTemplateResponse,
    ExportDraftRequest,
    RegenerateClauseRequest,
    UpdateDraftClauseRequest,
)
from ...services.audit import record_audit
from ...services.drafting import (
    create_draft,
    delete_draft,
    export_docx,
    get_draft,
    list_drafts,
    list_templates,
    regenerate_clause,
    update_clause,
)
from ...services.settings import effective_settings

router = APIRouter(prefix="/drafting", tags=["drafting"])
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(required_user)]


@router.get("/templates", response_model=list[DraftTemplateResponse])
async def templates(request: Request, session: Session, _user: CurrentUser) -> list[DraftTemplateResponse]:
    return await list_templates(session, request.app.state.settings)


@router.post("/drafts", response_model=DraftDetail, status_code=201)
async def create(
    payload: CreateDraftRequest, request: Request, session: Session, user: CurrentUser
) -> DraftDetail:
    generator = await _effective_generator(request, session)
    try:
        draft = await create_draft(
            session, request.app.state.settings, template_id=payload.template_id,
            title=payload.title, inputs=payload.inputs, user=user, generator=generator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="The language model provider is unavailable") from exc
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft template not found")
    return draft


@router.get("/drafts", response_model=list[DraftSummary])
async def drafts(request: Request, session: Session, user: CurrentUser) -> list[DraftSummary]:
    return await list_drafts(session, request.app.state.settings, user)


@router.get("/drafts/{draft_id}", response_model=DraftDetail)
async def detail(draft_id: UUID, request: Request, session: Session, user: CurrentUser) -> DraftDetail:
    draft = await get_draft(session, request.app.state.settings, draft_id, user)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.put("/drafts/{draft_id}/clauses/{clause_id}", response_model=DraftDetail)
async def edit_clause(
    draft_id: UUID, clause_id: UUID, payload: UpdateDraftClauseRequest,
    request: Request, session: Session, user: CurrentUser,
) -> DraftDetail:
    draft = await update_clause(
        session, request.app.state.settings, draft_id, clause_id,
        heading=payload.heading, body=payload.body, user=user,
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft or clause not found")
    return draft


@router.post("/drafts/{draft_id}/clauses/{clause_id}/regenerate", response_model=DraftDetail)
async def regenerate(
    draft_id: UUID, clause_id: UUID, payload: RegenerateClauseRequest,
    request: Request, session: Session, user: CurrentUser,
) -> DraftDetail:
    generator = await _effective_generator(request, session)
    try:
        draft = await regenerate_clause(
            session, request.app.state.settings, draft_id, clause_id,
            instruction=payload.instruction, user=user, generator=generator,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="The language model provider is unavailable") from exc
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft or clause not found")
    return draft


@router.post("/drafts/{draft_id}/export")
async def export(
    draft_id: UUID, payload: ExportDraftRequest, request: Request,
    session: Session, user: CurrentUser,
) -> Response:
    draft = await get_draft(session, request.app.state.settings, draft_id, user)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if payload.format == "pdf":
        raise HTTPException(status_code=501, detail="PDF export is not configured")
    await record_audit(
        session, request, user=user, action="draft_export", resource_type="draft",
        resource_id=draft.id, details={"format": payload.format},
    )
    return StreamingResponse(
        iter([export_docx(draft)]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{draft.title}.docx"'},
    )


@router.delete("/drafts/{draft_id}", status_code=204)
async def remove(draft_id: UUID, request: Request, session: Session, user: CurrentUser) -> Response:
    draft = await get_draft(session, request.app.state.settings, draft_id, user)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    deleted = await delete_draft(session, request.app.state.settings, draft_id, user)
    await record_audit(
        session, request, user=user, action="draft_delete", resource_type="draft",
        resource_id=draft_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
    return Response(status_code=204)


async def _effective_generator(request: Request, session: AsyncSession):
    effective = await effective_settings(session, request.app.state.settings)
    generator = request.app.state.generator
    return LLMGenerator(effective) if isinstance(generator, LLMGenerator) else generator