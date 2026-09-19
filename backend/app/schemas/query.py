"""Retrieval-augmented query API schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_id: UUID | None = None
    limit: int = Field(default=8, ge=1, le=20)
    reveal_pii: bool = False


class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    filename: str
    chunk_index: int
    score: float
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    provider: str
    model: str
    citations: list[Citation]
