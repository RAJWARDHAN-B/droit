"""Organization-scoped legal drafting workflows."""

from __future__ import annotations

from io import BytesIO
from uuid import UUID

from docx import Document as DocxDocument
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import Settings
from ..core.drafting import generate_clause
from ..core.generation import AnswerGenerator
from ..core.risk import score_document_risk
from ..models import (
    Draft,
    DraftClause,
    DraftClauseSource,
    DraftStatus,
    DraftTemplate,
    DraftVersion,
    Organization,
    User,
)
from ..schemas import (
    DraftClauseResponse,
    DraftDetail,
    DraftSummary,
    DraftTemplateResponse,
    DraftVersionResponse,
)
from .documents import get_or_create_organization

_BUILTIN_TEMPLATES = (
    {
        "slug": "nda",
        "name": "Non-Disclosure Agreement",
        "document_type": "NDA",
        "input_schema": {
            "disclosing_party": {"label": "Disclosing party", "required": True},
            "receiving_party": {"label": "Receiving party", "required": True},
            "purpose": {"label": "Purpose", "required": True},
            "term": {"label": "Term", "required": True},
        },
        "clause_outline": [
            {"heading": "Definitions", "purpose": "Define confidential information."},
            {"heading": "Confidentiality Obligations", "purpose": "Limit use and disclosure."},
            {"heading": "Permitted Disclosures", "purpose": "Describe required and permitted disclosures."},
            {"heading": "Term and Survival", "purpose": "Set the agreement and confidentiality periods."},
            {"heading": "Governing Law", "purpose": "Set a governing law placeholder."},
        ],
    },
    {
        "slug": "msa",
        "name": "Master Services Agreement",
        "document_type": "MSA",
        "input_schema": {
            "client": {"label": "Client", "required": True},
            "provider": {"label": "Service provider", "required": True},
            "services": {"label": "Services", "required": True},
            "fees": {"label": "Fees", "required": True},
        },
        "clause_outline": [
            {"heading": "Services", "purpose": "Describe the services and delivery standard."},
            {"heading": "Fees and Payment", "purpose": "Set invoicing and payment terms."},
            {"heading": "Confidentiality", "purpose": "Protect business information."},
            {"heading": "Limitation of Liability", "purpose": "Set a commercially balanced liability cap."},
            {"heading": "Termination", "purpose": "Set termination rights and effects."},
        ],
    },
    {
        "slug": "sow",
        "name": "Statement of Work",
        "document_type": "SOW",
        "input_schema": {
            "customer": {"label": "Customer", "required": True},
            "supplier": {"label": "Supplier", "required": True},
            "deliverables": {"label": "Deliverables", "required": True},
            "deadline": {"label": "Deadline", "required": True},
        },
        "clause_outline": [
            {"heading": "Scope", "purpose": "Define the agreed work."},
            {"heading": "Deliverables and Acceptance", "purpose": "Define delivery and acceptance."},
            {"heading": "Schedule", "purpose": "Set milestones and deadline."},
            {"heading": "Fees", "purpose": "Set the project price and payment."},
        ],
    },
    {
        "slug": "employment-agreement",
        "name": "Employment Agreement",
        "document_type": "Employment Agreement",
        "input_schema": {
            "employer": {"label": "Employer", "required": True},
            "employee": {"label": "Employee", "required": True},
            "role": {"label": "Role", "required": True},
            "salary": {"label": "Salary", "required": True},
        },
        "clause_outline": [
            {"heading": "Appointment and Duties", "purpose": "Define the role and duties."},
            {"heading": "Compensation", "purpose": "Set salary and payment terms."},
            {"heading": "Confidentiality and IP", "purpose": "Protect confidential information and work product."},
            {"heading": "Termination", "purpose": "Set termination rights."},
        ],
    },
    {
        "slug": "ip-assignment",
        "name": "IP Assignment Agreement",
        "document_type": "IP Assignment",
        "input_schema": {
            "assignor": {"label": "Assignor", "required": True},
            "assignee": {"label": "Assignee", "required": True},
            "work": {"label": "Work or invention", "required": True},
            "consideration": {"label": "Consideration", "required": True},
        },
        "clause_outline": [
            {"heading": "Assignment", "purpose": "Assign the identified intellectual property."},
            {"heading": "Further Assurances", "purpose": "Require cooperation for perfection."},
            {"heading": "Representations", "purpose": "Set ownership and authority representations."},
            {"heading": "Consideration", "purpose": "Record the consideration."},
        ],
    },
)


async def list_templates(session: AsyncSession, settings: Settings) -> list[DraftTemplateResponse]:
    organization = await get_or_create_organization(session, settings.default_org_id)
    await _ensure_builtins(session, organization.id)
    result = await session.execute(
        select(DraftTemplate).where(DraftTemplate.organization_id == organization.id).order_by(DraftTemplate.name)
    )
    return [_template_response(template) for template in result.scalars().all()]


async def create_template(
    session: AsyncSession,
    settings: Settings,
    *,
    name: str,
    document_type: str,
    input_schema: dict[str, dict[str, object]],
    clause_outline: list[dict[str, object]],
) -> DraftTemplateResponse:
    organization = await get_or_create_organization(session, settings.default_org_id)
    await _ensure_builtins(session, organization.id)
    template = DraftTemplate(
        organization_id=organization.id,
        slug=await _unique_slug(session, organization.id, name),
        name=name,
        document_type=document_type,
        input_schema=input_schema,
        clause_outline=clause_outline,
        is_builtin=False,
    )
    session.add(template)
    await session.flush()
    return _template_response(template)


async def update_template(
    session: AsyncSession,
    settings: Settings,
    template_id: UUID,
    *,
    name: str,
    document_type: str,
    input_schema: dict[str, dict[str, object]],
    clause_outline: list[dict[str, object]],
) -> DraftTemplateResponse | None:
    template = await _load_template(session, settings, template_id)
    if template is None:
        return None
    if template.is_builtin:
        raise PermissionError("Built-in templates cannot be modified")
    template.name = name
    template.document_type = document_type
    template.input_schema = input_schema
    template.clause_outline = clause_outline
    await session.flush()
    return _template_response(template)


async def delete_template(session: AsyncSession, settings: Settings, template_id: UUID) -> bool:
    template = await _load_template(session, settings, template_id)
    if template is None:
        return False
    if template.is_builtin:
        raise PermissionError("Built-in templates cannot be deleted")
    in_use = await session.scalar(
        select(Draft.id).where(Draft.template_id == template.id).limit(1)
    )
    if in_use is not None:
        raise ValueError("This template is still used by existing drafts")
    await session.delete(template)
    await session.flush()
    return True


async def create_draft(
    session: AsyncSession,
    settings: Settings,
    *,
    template_id: UUID,
    title: str,
    inputs: dict[str, str],
    user: User,
    generator: AnswerGenerator,
) -> DraftDetail | None:
    organization = await get_or_create_organization(session, settings.default_org_id)
    await _ensure_builtins(session, organization.id)
    template = await session.scalar(
        select(DraftTemplate).where(
            DraftTemplate.id == template_id, DraftTemplate.organization_id == organization.id
        )
    )
    if template is None:
        return None
    _validate_inputs(template, inputs)
    draft = Draft(
        organization_id=organization.id,
        user_id=user.id,
        template_id=template.id,
        title=title,
        inputs=inputs,
        risk_breakdown={},
    )
    session.add(draft)
    # The draft stays pending until the clauses exist, so appending never triggers a lazy load.
    await _generate_all(draft, template, inputs, generator)
    _snapshot(draft, user)
    await session.flush()
    return _detail(draft)


async def list_drafts(session: AsyncSession, settings: Settings, user: User) -> list[DraftSummary]:
    organization = await get_or_create_organization(session, settings.default_org_id)
    result = await session.execute(
        select(Draft).where(
            Draft.organization_id == organization.id, Draft.user_id == user.id
        ).order_by(Draft.updated_at.desc())
    )
    return [_summary(draft) for draft in result.scalars().all()]


async def get_draft(session: AsyncSession, settings: Settings, draft_id: UUID, user: User) -> DraftDetail | None:
    draft = await _load(session, settings, draft_id, user)
    return _detail(draft) if draft else None


async def update_clause(
    session: AsyncSession, settings: Settings, draft_id: UUID, clause_id: UUID,
    *, heading: str, body: str, user: User,
) -> DraftDetail | None:
    draft = await _load(session, settings, draft_id, user)
    if draft is None:
        return None
    clause = next((item for item in draft.clauses if item.id == clause_id), None)
    if clause is None:
        return None
    clause.heading = heading
    clause.body = body
    clause.source = DraftClauseSource.EDITED
    clause.version += 1
    _refresh_risk(draft)
    _snapshot(draft, user)
    await session.flush()
    return _detail(draft)


async def regenerate_clause(
    session: AsyncSession, settings: Settings, draft_id: UUID, clause_id: UUID,
    *, instruction: str | None, user: User, generator: AnswerGenerator,
) -> DraftDetail | None:
    draft = await _load(session, settings, draft_id, user)
    if draft is None:
        return None
    clause = next((item for item in draft.clauses if item.id == clause_id), None)
    if clause is None:
        return None
    template = draft.template
    generated = await generate_clause(
        generator,
        template_name=template.name,
        clause_heading=clause.heading,
        clause_outline=template.clause_outline,
        inputs=draft.inputs,
        prior_clauses=[item.body for item in draft.clauses if item.ordinal < clause.ordinal],
        instruction=instruction,
    )
    clause.heading = generated.heading
    clause.body = generated.body
    clause.rationale = generated.rationale
    clause.risk_notes = generated.risk_notes
    clause.source = DraftClauseSource.GENERATED
    clause.version += 1
    _refresh_risk(draft)
    _snapshot(draft, user)
    await session.flush()
    return _detail(draft)


async def delete_draft(session: AsyncSession, settings: Settings, draft_id: UUID, user: User) -> bool:
    draft = await _load(session, settings, draft_id, user)
    if draft is None:
        return False
    await session.delete(draft)
    await session.flush()
    return True


async def list_versions(
    session: AsyncSession, settings: Settings, draft_id: UUID, user: User
) -> list[DraftVersionResponse] | None:
    draft = await _load(session, settings, draft_id, user)
    if draft is None:
        return None
    return [_version_response(version) for version in draft.versions]


async def restore_version(
    session: AsyncSession, settings: Settings, draft_id: UUID, version: int, *, user: User
) -> DraftDetail | None:
    draft = await _load(session, settings, draft_id, user)
    if draft is None:
        return None
    snapshot = next((item for item in draft.versions if item.version == version), None)
    if snapshot is None:
        return None
    clauses = list(snapshot.snapshot.get("clauses", []))
    draft.title = str(snapshot.snapshot.get("title", draft.title))
    draft.clauses.clear()
    # The clause ordinals are unique per draft, so the removals must land before the inserts.
    await session.flush()
    for ordinal, clause in enumerate(clauses):
        draft.clauses.append(
            DraftClause(
                organization_id=draft.organization_id,
                ordinal=ordinal,
                heading=str(clause.get("heading", "")),
                body=str(clause.get("body", "")),
                rationale=str(clause.get("rationale", "")),
                risk_notes=list(clause.get("risk_notes", [])),
                source=DraftClauseSource(str(clause.get("source", DraftClauseSource.TEMPLATE.value))),
            )
        )
    _refresh_risk(draft)
    _snapshot(draft, user)
    await session.flush()
    return _detail(draft)


def export_docx(draft: DraftDetail) -> bytes:
    document = DocxDocument()
    document.add_heading(draft.title, level=0)
    for clause in draft.clauses:
        document.add_heading(clause.heading, level=1)
        document.add_paragraph(clause.body)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def export_pdf(draft: DraftDetail) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "DraftBody", parent=styles["BodyText"], alignment=TA_JUSTIFY, leading=15
    )
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        title=draft.title,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    flowables = [Paragraph(_escape_pdf(draft.title), styles["Title"]), Spacer(1, 6 * mm)]
    for clause in draft.clauses:
        flowables.append(Paragraph(_escape_pdf(clause.heading), styles["Heading2"]))
        for paragraph in clause.body.split("\n"):
            if paragraph.strip():
                flowables.append(Paragraph(_escape_pdf(paragraph), body_style))
        flowables.append(Spacer(1, 4 * mm))
    document.build(flowables)
    return output.getvalue()


def _escape_pdf(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def _ensure_builtins(session: AsyncSession, organization_id: UUID) -> None:
    existing = set((await session.scalars(select(DraftTemplate.slug).where(DraftTemplate.organization_id == organization_id))).all())
    for definition in _BUILTIN_TEMPLATES:
        if definition["slug"] not in existing:
            session.add(DraftTemplate(organization_id=organization_id, is_builtin=True, **definition))
    await session.flush()


async def _generate_all(draft: Draft, template: DraftTemplate, inputs: dict[str, str], generator: AnswerGenerator) -> None:
    prior: list[str] = []
    for ordinal, outline in enumerate(template.clause_outline):
        generated = await generate_clause(
            generator,
            template_name=template.name,
            clause_heading=str(outline["heading"]),
            clause_outline=template.clause_outline,
            inputs=inputs,
            prior_clauses=prior,
        )
        draft.clauses.append(DraftClause(
            organization_id=draft.organization_id,
            ordinal=ordinal,
            heading=generated.heading,
            body=generated.body,
            rationale=generated.rationale,
            risk_notes=generated.risk_notes,
            source=DraftClauseSource.GENERATED,
        ))
        prior.append(generated.body)
    _refresh_risk(draft)


def _refresh_risk(draft: Draft) -> None:
    assessment = score_document_risk("\n\n".join(clause.body for clause in draft.clauses))
    draft.risk_breakdown = {"score": assessment.score, **assessment.breakdown}


def _snapshot(draft: Draft, user: User) -> None:
    version = len(draft.versions) + 1
    draft.versions.append(DraftVersion(
        organization_id=draft.organization_id,
        version=version,
        created_by=user.id,
        snapshot={"title": draft.title, "clauses": [
            {
                "heading": clause.heading,
                "body": clause.body,
                "rationale": clause.rationale,
                "risk_notes": list(clause.risk_notes),
                "source": clause.source.value,
            }
            for clause in draft.clauses
        ]},
    ))


async def _load_template(
    session: AsyncSession, settings: Settings, template_id: UUID
) -> DraftTemplate | None:
    organization = await get_or_create_organization(session, settings.default_org_id)
    return await session.scalar(
        select(DraftTemplate).where(
            DraftTemplate.id == template_id,
            DraftTemplate.organization_id == organization.id,
        )
    )


async def _unique_slug(session: AsyncSession, organization_id: UUID, name: str) -> str:
    base = slugify(name)[:90] or "template"
    taken = set(
        (
            await session.scalars(
                select(DraftTemplate.slug).where(
                    DraftTemplate.organization_id == organization_id,
                    DraftTemplate.slug.like(f"{base}%"),
                )
            )
        ).all()
    )
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


async def _load(session: AsyncSession, settings: Settings, draft_id: UUID, user: User) -> Draft | None:
    organization = await get_or_create_organization(session, settings.default_org_id)
    result = await session.execute(
        select(Draft).options(selectinload(Draft.template), selectinload(Draft.clauses), selectinload(Draft.versions)).where(
            Draft.id == draft_id, Draft.organization_id == organization.id, Draft.user_id == user.id
        )
    )
    return result.scalar_one_or_none()


def _validate_inputs(template: DraftTemplate, inputs: dict[str, str]) -> None:
    required = [key for key, definition in template.input_schema.items() if definition.get("required")]
    missing = [key for key in required if not inputs.get(key, "").strip()]
    if missing:
        raise ValueError(f"Missing required inputs: {', '.join(missing)}")


def _template_response(template: DraftTemplate) -> DraftTemplateResponse:
    return DraftTemplateResponse.model_validate(template, from_attributes=True)


def _version_response(version: DraftVersion) -> DraftVersionResponse:
    return DraftVersionResponse(
        version=version.version,
        title=str(version.snapshot.get("title", "")),
        clause_count=len(version.snapshot.get("clauses", [])),
        created_by=version.created_by,
        created_at=version.created_at,
    )


def _summary(draft: Draft) -> DraftSummary:
    return DraftSummary.model_validate(draft, from_attributes=True)


def _detail(draft: Draft) -> DraftDetail:
    return DraftDetail(
        id=draft.id, title=draft.title, template_id=draft.template_id, status=draft.status,
        updated_at=draft.updated_at, inputs=draft.inputs, risk_breakdown=draft.risk_breakdown,
        clauses=[DraftClauseResponse.model_validate(clause, from_attributes=True) for clause in draft.clauses],
        version=len(draft.versions),
    )
