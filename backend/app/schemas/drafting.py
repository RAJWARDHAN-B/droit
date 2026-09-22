"""Legal drafting request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..models import DraftClauseSource, DraftStatus


class DraftTemplateResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    document_type: str
    input_schema: dict[str, object]
    clause_outline: list[dict[str, object]]
    is_builtin: bool


class DraftTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    document_type: str = Field(min_length=1, max_length=100)
    input_schema: dict[str, dict[str, object]] = Field(default_factory=dict)
    clause_outline: list[dict[str, object]] = Field(min_length=1)

    @field_validator("input_schema")
    @classmethod
    def _labelled_inputs(
        cls, value: dict[str, dict[str, object]]
    ) -> dict[str, dict[str, object]]:
        for key, definition in value.items():
            if not str(definition.get("label", "")).strip():
                raise ValueError(f"Input '{key}' needs a label")
        return value

    @field_validator("clause_outline")
    @classmethod
    def _headed_clauses(cls, value: list[dict[str, object]]) -> list[dict[str, object]]:
        for entry in value:
            if not str(entry.get("heading", "")).strip():
                raise ValueError("Every clause in the outline needs a heading")
        return value


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


class DraftVersionResponse(BaseModel):
    version: int
    title: str
    clause_count: int
    created_by: UUID
    created_at: datetime


class ExportDraftRequest(BaseModel):
    format: str = Field(pattern="^(docx|pdf)$")