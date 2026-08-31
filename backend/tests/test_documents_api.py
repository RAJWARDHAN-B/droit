"""Integration tests for document ingestion against the configured database."""

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.config import Settings
from backend.app.database import create_engine
from backend.app.main import create_app
from backend.app.models import Organization


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

    try:
        with TestClient(create_app(settings)) as client:
            first = client.post(
                "/api/v1/documents/paste",
                headers={"Idempotency-Key": "paste-integration-contract-v1"},
                json={
                    "title": "Mutual NDA",
                    "text": "The parties shall keep confidential information private.",
                },
            )
            repeated = client.post(
                "/api/v1/documents/paste",
                headers={"Idempotency-Key": "paste-integration-contract-v1"},
                json={
                    "title": "Mutual NDA",
                    "text": "The parties shall keep confidential information private.",
                },
            )
            fetched = client.get(f"/api/v1/jobs/{first.json()['job_id']}")

        assert first.status_code == 201
        assert first.json()["filename"] == "Mutual NDA.txt"
        assert first.json()["document_status"] == "processing"
        assert first.json()["stage"] == "pii_scan"
        assert repeated.status_code == 200
        assert repeated.json()["job_id"] == first.json()["job_id"]
        assert fetched.status_code == 200
        assert fetched.json() == first.json()

        stored_files = list(settings.upload_directory.iterdir())
        assert len(stored_files) == 2
        assert any(path.name.endswith("_original.txt") for path in stored_files)
        assert any(path.name.endswith("_raw_text.txt") for path in stored_files)
    finally:
        asyncio.run(_delete_test_organization(settings))


def test_upload_rejects_unsupported_format(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("notes.md", b"not a supported document", "text/markdown")},
        )

    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["detail"]