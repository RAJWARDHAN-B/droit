"""Legal drafting request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import DraftClauseSource, DraftStatus


class DraftTemplateResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    document_type: str
    input_schema: dict[str, object]
    clause_outline: list[dict[str, object]]
    is_builtin: bool


class CreateDraftRequest(BaseModel):
    template_id: UUID
    title: str = Field(min_length=1, max_length=240)
    inputs: dict[str, str] = Field(default_factory=dict)


class DraftClauseResponse(BaseModel):
    id: UUID
    ordinal: int
    heading: str
    body: str
    rationale: str
    risk_notes: list[str]
    source: DraftClauseSource
    version: int


class DraftSummary(BaseModel):
    id: UUID
    title: str
    template_id: UUID
    status: DraftStatus
    updated_at: datetime


class DraftDetail(DraftSummary):
    inputs: dict[str, str]
    risk_breakdown: dict[str, object]
    clauses: list[DraftClauseResponse]
    version: int


class UpdateDraftClauseRequest(BaseModel):
    heading: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1)


class RegenerateClauseRequest(BaseModel):
    instruction: str | None = Field(default=None, max_length=1000)


class ExportDraftRequest(BaseModel):
    format: str = Field(pattern="^(docx|pdf)$")