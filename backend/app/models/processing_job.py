"""Idempotent document processing job state."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .document import Document


class ProcessingStage(str, Enum):
    UPLOADING = "uploading"
    EXTRACTING = "extracting"
    PII_SCAN = "pii_scan"
    INDEXING = "indexing"
    DONE = "done"
    FAILED = "failed"


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_jobs"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    stage: Mapped[ProcessingStage] = mapped_column(
        SQLEnum(ProcessingStage, name="processing_stage", native_enum=False),
        default=ProcessingStage.UPLOADING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="jobs")