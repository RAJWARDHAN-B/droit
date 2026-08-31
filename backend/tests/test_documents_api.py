"""Integration tests for document ingestion against the configured database."""

import asyncio
from pathlib import Path
from uuid import UUID
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.config import Settings
from backend.app.core.embedding import ChunkVector
from backend.app.database import create_engine
from backend.app.main import create_app
from backend.app.models import Organization


class RecordingVectorIndexer:
    def __init__(self) -> None:
        self.chunks: list[ChunkVector] = []
        self.deleted: list[UUID] = []

    async def index(
        self,
        *,
        document_id: UUID,
        organization_id: UUID,
        chunks: list[ChunkVector],
    ) -> None:
        self.chunks.extend(chunks)

    async def delete(self, point_ids: list[UUID]) -> None:
        self.deleted.extend(point_ids)


async def _delete_test_organization(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                delete(Organization).where(Organization.slug == settings.default_org_id)
            )
    finally:
        await engine.dispose()


def test_paste_document_is_persisted_and_idempotent(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    vector_indexer = RecordingVectorIndexer()

    try:
        with TestClient(create_app(settings, vector_indexer=vector_indexer)) as client:
            first = client.post(
                "/api/v1/documents/paste",
                headers={"Idempotency-Key": "paste-integration-contract-v1"},
                json={
                    "title": "Mutual NDA",
                    "text": "Email jane@example.com. Contact jane@example.com only.",
                },
            )
            repeated = client.post(
                "/api/v1/documents/paste",
                headers={"Idempotency-Key": "paste-integration-contract-v1"},
                json={
                    "title": "Mutual NDA",
                    "text": "Email jane@example.com. Contact jane@example.com only.",
                },
            )
            fetched = client.get(f"/api/v1/jobs/{first.json()['job_id']}")

        assert first.status_code == 201
        assert first.json()["filename"] == "Mutual NDA.txt"
        assert first.json()["document_status"] == "ready"
        assert first.json()["stage"] == "done"
        assert repeated.status_code == 200
        assert repeated.json()["job_id"] == first.json()["job_id"]
        assert fetched.status_code == 200
        assert fetched.json() == first.json()
        assert len(vector_indexer.chunks) == 1
        assert vector_indexer.chunks[0].text == "Email [EMAIL_1]. Contact [EMAIL_1] only."

        stored_files = list(settings.upload_directory.iterdir())
        assert len(stored_files) == 3
        assert any(path.name.endswith("_original.txt") for path in stored_files)
        assert any(path.name.endswith("_raw_text.txt") for path in stored_files)
        anonymized_path = next(
            path for path in stored_files if path.name.endswith("_anonymized_text.txt")
        )
        assert anonymized_path.read_text() == "Email [EMAIL_1]. Contact [EMAIL_1] only."
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_upload_rejects_unsupported_format(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)

    with TestClient(create_app(settings, vector_indexer=RecordingVectorIndexer())) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("notes.md", b"not a supported document", "text/markdown")},
        )

    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]


def test_delete_removes_database_vectors_and_local_files(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    vector_indexer = RecordingVectorIndexer()

    try:
        with TestClient(create_app(settings, vector_indexer=vector_indexer)) as client:
            created = client.post(
                "/api/v1/documents/paste",
                json={"title": "Delete me", "text": "A short legal agreement."},
            )
            document_id = created.json()["document_id"]
            job_id = created.json()["job_id"]
            indexed_ids = [chunk.point_id for chunk in vector_indexer.chunks]

            deleted = client.delete(f"/api/v1/documents/{document_id}")
            missing_document = client.delete(f"/api/v1/documents/{document_id}")
            missing_job = client.get(f"/api/v1/jobs/{job_id}")

        assert created.status_code == 201
        assert deleted.status_code == 204
        assert missing_document.status_code == 404
        assert missing_job.status_code == 404
        assert vector_indexer.deleted == indexed_ids
        assert list(settings.upload_directory.iterdir()) == []
    finally:
        asyncio.run(_delete_test_organization(settings))