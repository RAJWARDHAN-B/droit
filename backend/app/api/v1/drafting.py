"""Protected legal drafting endpoints."""

from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import AdminUser, required_user
from ...core.generation import LLMGenerator
from ...database import get_session
from ...models import User
from ...schemas import (
    CreateDraftRequest,
    DraftDetail,
    DraftSummary,
    DraftTemplateRequest,
    DraftTemplateResponse,
    DraftVersionResponse,
    ExportDraftRequest,
    RegenerateClauseRequest,
    UpdateDraftClauseRequest,
)
from ...services.audit import record_audit
from ...services.drafting import (
    create_draft,
    create_template,
    delete_draft,
    delete_template,
    export_docx,
    export_pdf,
    get_draft,
    list_drafts,
    list_templates,
    list_versions,
    regenerate_clause,
    restore_version,
    update_clause,
    update_template,
)
from ...services.settings import effective_settings

router = APIRouter(prefix="/drafting", tags=["drafting"])
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(required_user)]
_EXPORT_MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


@router.get("/templates", response_model=list[DraftTemplateResponse])
async def templates(request: Request, session: Session, _user: CurrentUser) -> list[DraftTemplateResponse]:
    return await list_templates(session, request.app.state.settings)


@router.post("/templates", response_model=DraftTemplateResponse, status_code=201)
async def add_template(
    payload: DraftTemplateRequest, request: Request, session: Session, user: AdminUser
) -> DraftTemplateResponse:
    template = await create_template(
        session, request.app.state.settings, name=payload.name,
        document_type=payload.document_type, input_schema=payload.input_schema,
        clause_outline=payload.clause_outline,
    )
    await record_audit(
        session, request, user=user, action="draft_template_create",
        resource_type="draft_template", resource_id=template.id,
    )
    return template


@router.put("/templates/{template_id}", response_model=DraftTemplateResponse)
async def edit_template(
    template_id: UUID, payload: DraftTemplateRequest, request: Request,
    session: Session, user: AdminUser,
) -> DraftTemplateResponse:
    try:
        template = await update_template(
            session, request.app.state.settings, template_id, name=payload.name,
            document_type=payload.document_type, input_schema=payload.input_schema,
            clause_outline=payload.clause_outline,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if template is None:
        raise HTTPException(status_code=404, detail="Draft template not found")
    await record_audit(
        session, request, user=user, action="draft_template_update",
        resource_type="draft_template", resource_id=template_id,
    )
    return template


@router.delete("/templates/{template_id}", status_code=204)
async def remove_template(
    template_id: UUID, request: Request, session: Session, user: AdminUser
) -> Response:
    try:
        deleted = await delete_template(session, request.app.state.settings, template_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft template not found")
    await record_audit(
        session, request, user=user, action="draft_template_delete",
        resource_type="draft_template", resource_id=template_id,
    )
    return Response(status_code=204)


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


@router.get("/drafts/{draft_id}/versions", response_model=list[DraftVersionResponse])
async def versions(
    draft_id: UUID, request: Request, session: Session, user: CurrentUser
) -> list[DraftVersionResponse]:
    history = await list_versions(session, request.app.state.settings, draft_id, user)
    if history is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return history


@router.post("/drafts/{draft_id}/versions/{version}/restore", response_model=DraftDetail)
async def restore(
    draft_id: UUID, version: int, request: Request, session: Session, user: CurrentUser
) -> DraftDetail:
    draft = await restore_version(
        session, request.app.state.settings, draft_id, version, user=user
    )
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft or version not found")
    await record_audit(
        session, request, user=user, action="draft_version_restore",
        resource_type="draft", resource_id=draft_id, details={"version": version},
    )
    return draft


@router.post("/drafts/{draft_id}/export")
async def export(
    draft_id: UUID, payload: ExportDraftRequest, request: Request,
    session: Session, user: CurrentUser,
) -> Response:
    draft = await get_draft(session, request.app.state.settings, draft_id, user)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    content = export_pdf(draft) if payload.format == "pdf" else export_docx(draft)
    await record_audit(
        session, request, user=user, action="draft_export", resource_type="draft",
        resource_id=draft.id, details={"format": payload.format},
    )
    return StreamingResponse(
        iter([content]),
        media_type=_EXPORT_MEDIA_TYPES[payload.format],
        headers={"Content-Disposition": f'attachment; filename="{draft.title}.{payload.format}"'},
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