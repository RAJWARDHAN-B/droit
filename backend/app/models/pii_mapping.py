"""Encrypted mappings between document aliases and original PII."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from .document import Document


class PIIMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pii_mappings"
    __table_args__ = (UniqueConstraint("document_id", "alias"),)

    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    original_value_encrypted: Mapped[bytes] = mapped_column(LargeBinary)

    document: Mapped[Document] = relationship(back_populates="pii_mappings")