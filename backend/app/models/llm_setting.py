"""Encrypted, organization-level LLM configuration."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "llm_settings"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(200))
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)