"""Persisted conversation API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import MessageRole
from .query import Citation


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    document_id: UUID | None = None


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)


class SendMessageRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    limit: int = Field(default=8, ge=1, le=20)


class ConversationMessageResponse(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    citations: list[Citation]
    provider: str | None
    model: str | None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    document_id: UUID | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessageResponse]
