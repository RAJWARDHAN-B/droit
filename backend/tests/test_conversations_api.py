"""Persisted conversation history coverage."""

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
    async def index(
        self, *, document_id: UUID, organization_id: UUID, chunks: list[ChunkVector]
    ) -> None:
        return None

    async def delete(self, point_ids: list[UUID]) -> None:
        return None


class EmptyVectorSearcher:
    async def search(
        self, query: str, *, organization_id: UUID, document_id: UUID | None, limit: int
    ) -> list[UUID]:
        return []


class StubGenerator:
    async def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        *,
        system_prompt: str | None = None,
    ) -> GeneratedAnswer:
        return GeneratedAnswer(
            answer="Either party may terminate with notice [1]. Contact [EMAIL_1].",
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


def _build_app(settings: Settings):
    return create_app(
        settings,
        vector_indexer=RecordingVectorIndexer(),
        retriever=HybridRetriever(EmptyVectorSearcher(), settings),
        generator=StubGenerator(),
    )


def test_conversation_persists_messages_citations_and_title(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings)) as client:
            document_id = client.post(
                "/api/v1/documents/paste",
                json={
                    "title": "Services Agreement",
                    "text": "Contact jane@example.com. Either party may terminate this agreement with thirty days written notice.",
                },
            ).json()["document_id"]

            created = client.post(
                "/api/v1/conversations", json={"document_id": document_id}
            )
            conversation_id = created.json()["id"]
            answered = client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"question": "When may either party terminate the agreement?"},
            )
            listed = client.get("/api/v1/conversations")
            reloaded = client.get(f"/api/v1/conversations/{conversation_id}")

        body = answered.json()
        assert created.status_code == 201
        assert answered.status_code == 200
        assert [message["role"] for message in body["messages"]] == ["user", "assistant"]
        assert body["messages"][1]["citations"][0]["filename"] == "Services Agreement.txt"
        assert body["title"].startswith("When may either party terminate")
        assert listed.json()[0]["message_count"] == 2
        # History reopens with the stored exchange intact.
        assert reloaded.json()["messages"][1]["content"] == body["messages"][1]["content"]
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_stored_history_keeps_pii_aliases(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings)) as client:
            client.post(
                "/api/v1/documents/paste",
                json={
                    "title": "Agreement",
                    "text": "Contact jane@example.com about termination notices.",
                },
            )
            conversation_id = client.post("/api/v1/conversations", json={}).json()["id"]
            client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"question": "Who should I contact about termination?"},
            )
            reloaded = client.get(f"/api/v1/conversations/{conversation_id}")

        assert "jane@example.com" not in reloaded.text
        assert "[EMAIL_1]" in reloaded.json()["messages"][1]["content"]
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_conversations_can_be_renamed_and_deleted(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings)) as client:
            conversation_id = client.post("/api/v1/conversations", json={}).json()["id"]
            renamed = client.patch(
                f"/api/v1/conversations/{conversation_id}",
                json={"title": "Termination review"},
            )
            deleted = client.delete(f"/api/v1/conversations/{conversation_id}")
            missing = client.get(f"/api/v1/conversations/{conversation_id}")

        assert renamed.json()["title"] == "Termination review"
        assert deleted.status_code == 204
        assert missing.status_code == 404
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_conversation_rejects_a_document_from_another_organization(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    with TestClient(_build_app(settings)) as client:
        response = client.post(
            "/api/v1/conversations", json={"document_id": str(uuid4())}
        )

    assert response.status_code == 404
