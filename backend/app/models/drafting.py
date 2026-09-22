"""Persisted legal drafting templates, drafts, clauses, and versions."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .organization import Organization, User


class DraftStatus(str, Enum):
    DRAFT = "draft"
    FINAL = "final"


class DraftClauseSource(str, Enum):
    GENERATED = "generated"
    EDITED = "edited"
    TEMPLATE = "template"


class DraftTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_templates"
    __table_args__ = (UniqueConstraint("organization_id", "slug"),)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(100))
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    clause_outline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    is_builtin: Mapped[bool] = mapped_column(default=False)

    organization: Mapped[Organization] = relationship()
    drafts: Mapped[list[Draft]] = relationship(back_populates="template")


class Draft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drafts"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("draft_templates.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[DraftStatus] = mapped_column(
        SQLEnum(DraftStatus, name="draft_status", native_enum=False), default=DraftStatus.DRAFT
    )
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk_breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    template: Mapped[DraftTemplate] = relationship(back_populates="drafts")
    clauses: Mapped[list[DraftClause]] = relationship(
        back_populates="draft", cascade="all, delete-orphan", order_by="DraftClause.ordinal"
    )
    versions: Mapped[list[DraftVersion]] = relationship(
        back_populates="draft", cascade="all, delete-orphan", order_by="DraftVersion.version"
    )


class DraftClause(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_clauses"
    __table_args__ = (UniqueConstraint("draft_id", "ordinal"),)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    risk_notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    source: Mapped[DraftClauseSource] = mapped_column(
        SQLEnum(DraftClauseSource, name="draft_clause_source", native_enum=False),
        default=DraftClauseSource.GENERATED,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    draft: Mapped[Draft] = relationship(back_populates="clauses")


class DraftVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "draft_versions"
    __table_args__ = (UniqueConstraint("draft_id", "version"),)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    draft: Mapped[Draft] = relationship(back_populates="versions")
    user: Mapped[User] = relationship()