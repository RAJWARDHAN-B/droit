"""Document ingestion API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..models import DocumentStatus, ProcessingStage


class PasteDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1)


class ProcessingJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    document_id: UUID
    filename: str
    document_status: DocumentStatus
    stage: ProcessingStage
    error_message: str | None
    created_at: datetime
    updated_at: datetime