"""Authentication, role, encrypted settings, and audit coverage."""

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from backend.app.config import Settings
from backend.app.database import create_engine
from backend.app.main import create_app
from backend.app.models import AuditLog, Organization


async def _delete_test_organization(settings: Settings) -> None:
    engine = create_engine(settings)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                delete(Organization).where(Organization.slug == settings.default_org_id)
            )
    finally:
        await engine.dispose()


def test_bootstrap_login_and_admin_settings_are_audited(tmp_path: Path) -> None:
    settings = Settings(
        storage_root=tmp_path,
        default_org_id=f"test-{uuid4().hex}",
        auth_required=True,
    )

    try:
        with TestClient(create_app(settings)) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={"email": "admin@example.com", "password": "a-very-secure-password"},
            )
            token = registration.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            unauthenticated = client.get("/api/v1/settings/llm")
            saved = client.put(
                "/api/v1/settings/llm",
                headers=headers,
                json={
                    "provider": "ollama",
                    "model": "llama3.2",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "local-secret",
                },
            )
            fetched = client.get("/api/v1/settings/llm", headers=headers)

        assert registration.status_code == 201
        assert unauthenticated.status_code == 401
        assert saved.status_code == 200
        assert fetched.status_code == 200
        assert fetched.json()["api_key_configured"] is True
        assert "local-secret" not in fetched.text

        async def read_audit_details() -> dict[str, object] | None:
            engine = create_engine(settings)
            try:
                async with engine.connect() as connection:
                    result = await connection.execute(
                        select(AuditLog.details).where(
                            AuditLog.action == "llm_settings.updated"
                        )
                    )
                    return result.scalar_one_or_none()
            finally:
                await engine.dispose()

        assert asyncio.run(read_audit_details()) == {}
    finally:
        asyncio.run(_delete_test_organization(settings))
