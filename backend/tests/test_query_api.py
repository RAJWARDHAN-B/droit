"""Integration tests for the retrieval-augmented query endpoint."""

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.config import Settings
from backend.app.core.embedding import ChunkVector
from backend.app.core.generation import GeneratedAnswer
from backend.app.core.retrieval import HybridRetriever, RetrievedChunk
from backend.app.database import create_engine
from backend.app.main import create_app
from backend.app.models import Organization


class RecordingVectorIndexer:
    def __init__(self) -> None:
        self.chunks: list[ChunkVector] = []
        self.deleted: list[UUID] = []

    async def index(
        self, *, document_id: UUID, organization_id: UUID, chunks: list[ChunkVector]
    ) -> None:
        self.chunks.extend(chunks)

    async def delete(self, point_ids: list[UUID]) -> None:
        self.deleted.extend(point_ids)


class EmptyVectorSearcher:
    """Forces BM25-only ranking so retrieval runs without a live Qdrant."""

    async def search(
        self, query: str, *, organization_id: UUID, document_id: UUID | None, limit: int
    ) -> list[UUID]:
        return []


class StubGenerator:
    def __init__(self) -> None:
        self.calls: list[list[RetrievedChunk]] = []

    async def generate(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> GeneratedAnswer:
        self.calls.append(chunks)
        return GeneratedAnswer(
            answer="Either party may terminate with thirty days notice [1].",
            provider="stub",
            model="stub-model",
        )


async def _delete_test_organization(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                delete(Organization).where(Organization.slug == settings.default_org_id)
            )
    finally:
        await engine.dispose()


def _build_app(settings: Settings, generator: StubGenerator):
    return create_app(
        settings,
        vector_indexer=RecordingVectorIndexer(),
        retriever=HybridRetriever(EmptyVectorSearcher(), settings),
        generator=generator,
    )


def test_query_answers_from_indexed_document_with_citations(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    generator = StubGenerator()

    try:
        with TestClient(_build_app(settings, generator)) as client:
            client.post(
                "/api/v1/documents/paste",
                json={
                    "title": "Services Agreement",
                    "text": "Either party may terminate this agreement with thirty days written notice.",
                },
            )
            response = client.post(
                "/api/v1/query",
                json={"question": "When may either party terminate the agreement?"},
            )

        body = response.json()
        assert response.status_code == 200
        assert body["answer"].startswith("Either party may terminate")
        assert body["provider"] == "stub"
        assert len(body["citations"]) == 1
        assert body["citations"][0]["filename"] == "Services Agreement.txt"
        assert "terminate" in body["citations"][0]["excerpt"]
        assert generator.calls, "The generator should receive retrieved context"
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_query_without_indexed_documents_skips_the_model(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    generator = StubGenerator()

    with TestClient(_build_app(settings, generator)) as client:
        response = client.post(
            "/api/v1/query", json={"question": "How does termination work?"}
        )

    body = response.json()
    assert response.status_code == 200
    assert body["citations"] == []
    assert "No indexed content" in body["answer"]
    assert generator.calls == []


def test_documents_library_lists_uploaded_documents(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings, StubGenerator())) as client:
            client.post(
                "/api/v1/documents/paste",
                json={"title": "NDA", "text": "Confidential information stays secret."},
            )
            response = client.get("/api/v1/documents")

        body = response.json()
        assert response.status_code == 200
        assert len(body) == 1
        assert body[0]["filename"] == "NDA.txt"
        assert body[0]["status"] == "ready"
        assert body[0]["chunk_count"] == 1
        assert body[0]["risk_score"] == 55
        assert "limitation_of_liability" in body[0]["risk_breakdown"]["missing_clauses"]
    finally:
        asyncio.run(_delete_test_organization(settings))
