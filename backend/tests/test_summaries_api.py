"""Legal and layman document summary coverage."""

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
    def __init__(self) -> None:
        self.system_prompts: list[str | None] = []

    async def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        *,
        system_prompt: str | None = None,
    ) -> GeneratedAnswer:
        self.system_prompts.append(system_prompt)
        return GeneratedAnswer(
            answer="Summary mentioning [PERSON_1].", provider="stub", model="stub-model"
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


def test_summaries_are_style_specific_and_cached(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    generator = StubGenerator()

    try:
        with TestClient(_build_app(settings, generator)) as client:
            document_id = client.post(
                "/api/v1/documents/paste",
                json={
                    "title": "NDA",
                    "text": "Jane Roe agrees that confidential information stays secret.",
                },
            ).json()["document_id"]

            legal = client.post(
                f"/api/v1/documents/{document_id}/summary", json={"style": "legal"}
            )
            layman = client.post(
                f"/api/v1/documents/{document_id}/summary", json={"style": "layman"}
            )
            repeated = client.post(
                f"/api/v1/documents/{document_id}/summary", json={"style": "legal"}
            )
            refreshed = client.post(
                f"/api/v1/documents/{document_id}/summary",
                json={"style": "legal", "refresh": True},
            )

        assert legal.status_code == 200
        assert legal.json()["cached"] is False
        assert layman.json()["style"] == "layman"
        assert repeated.json()["cached"] is True
        assert refreshed.json()["cached"] is False
        # Cached reads must not call the provider again.
        assert len(generator.system_prompts) == 3
        assert "practising lawyers" in generator.system_prompts[0]
        assert "no legal training" in generator.system_prompts[1]
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_summary_for_unknown_document_returns_404(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    with TestClient(_build_app(settings, StubGenerator())) as client:
        response = client.post(
            f"/api/v1/documents/{uuid4()}/summary", json={"style": "legal"}
        )

    assert response.status_code == 404
