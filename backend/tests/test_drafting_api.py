"""Drafting API authentication, scoping, regeneration, export, and version coverage."""

import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from backend.app.config import Settings
from backend.app.core.auth import hash_password
from backend.app.core.embedding import ChunkVector
from backend.app.core.generation import GeneratedAnswer
from backend.app.core.retrieval import HybridRetriever, RetrievedChunk
from backend.app.database import create_engine, create_session_factory
from backend.app.main import create_app
from backend.app.models import AuditLog, Organization, User, UserRole

_INPUTS = {
    "disclosing_party": "Acme Legal LLC",
    "receiving_party": "Jane Roe",
    "purpose": "Evaluating a commercial partnership",
    "term": "24 months",
}
_PASSWORD = "a-very-secure-password"


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


class StubClauseGenerator:
    """Return aliased clause JSON and record every prompt sent to the provider."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        *,
        system_prompt: str | None = None,
    ) -> GeneratedAnswer:
        self.prompts.append(question)
        return GeneratedAnswer(
            answer=json.dumps(
                {
                    "heading": "Confidentiality",
                    "body": "[INPUT_2] shall protect information disclosed for [INPUT_1].",
                    "rationale": "Keeps disclosure limited to the stated purpose.",
                    "risk_notes": ["Confirm the survival period."],
                }
            ),
            provider="stub",
            model="stub-model",
        )


def _build_app(settings: Settings, generator: StubClauseGenerator):
    return create_app(
        settings,
        vector_indexer=RecordingVectorIndexer(),
        retriever=HybridRetriever(EmptyVectorSearcher(), settings),
        generator=generator,
    )


async def _delete_test_organizations(*slugs: str) -> None:
    engine = create_engine(Settings())
    try:
        async with engine.begin() as connection:
            await connection.execute(
                delete(Organization).where(Organization.slug.in_(slugs))
            )
    finally:
        await engine.dispose()


async def _seed_organization_user(settings: Settings, email: str) -> None:
    engine = create_engine(settings)
    try:
        async with create_session_factory(engine)() as session:
            organization = Organization(
                slug=settings.default_org_id, name="Second Organization"
            )
            session.add(organization)
            await session.flush()
            session.add(
                User(
                    organization_id=organization.id,
                    email=email,
                    password_hash=hash_password(_PASSWORD),
                    role=UserRole.ADMIN,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


async def _read_audit_actions(settings: Settings, action: str) -> list[dict[str, object]]:
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                select(AuditLog.details).where(AuditLog.action == action)
            )
            return [row[0] for row in result.all()]
    finally:
        await engine.dispose()


def _register(client: TestClient, email: str = "drafter@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": _PASSWORD}
    )
    assert response.status_code == 201


def _create_draft(client: TestClient) -> dict[str, object]:
    templates = client.get("/api/v1/drafting/templates").json()
    template_id = next(item["id"] for item in templates if item["slug"] == "nda")
    response = client.post(
        "/api/v1/drafting/drafts",
        json={"template_id": template_id, "title": "Mutual NDA", "inputs": _INPUTS},
    )
    assert response.status_code == 201
    return response.json()


def test_drafting_requires_authentication_and_scopes_to_the_organization(
    tmp_path: Path,
) -> None:
    first = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    second = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(first, StubClauseGenerator())) as client:
            client.cookies.clear()
            anonymous_templates = client.get("/api/v1/drafting/templates")
            anonymous_drafts = client.get("/api/v1/drafting/drafts")

            _register(client)
            draft = _create_draft(client)
            owned = client.get("/api/v1/drafting/drafts")

        asyncio.run(_seed_organization_user(second, "other-org@example.com"))

        with TestClient(_build_app(second, StubClauseGenerator())) as client:
            client.post(
                "/api/v1/auth/login",
                json={"email": "other-org@example.com", "password": _PASSWORD},
            )
            cross_org_list = client.get("/api/v1/drafting/drafts")
            cross_org_detail = client.get(f"/api/v1/drafting/drafts/{draft['id']}")
            cross_org_export = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/export", json={"format": "docx"}
            )

        assert anonymous_templates.status_code == 401
        assert anonymous_drafts.status_code == 401
        assert [item["id"] for item in owned.json()] == [draft["id"]]
        assert cross_org_list.json() == []
        assert cross_org_detail.status_code == 404
        assert cross_org_export.status_code == 404
    finally:
        asyncio.run(
            _delete_test_organizations(first.default_org_id, second.default_org_id)
        )


def test_regeneration_keeps_prior_clauses_aliased(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")
    generator = StubClauseGenerator()

    try:
        with TestClient(_build_app(settings, generator)) as client:
            _register(client)
            draft = _create_draft(client)
            last_clause = draft["clauses"][-1]
            generator.prompts.clear()

            regenerated = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/clauses/{last_clause['id']}/regenerate",
                json={"instruction": f"Name {_INPUTS['receiving_party']} explicitly."},
            )

        assert regenerated.status_code == 200
        body = regenerated.json()
        clause = body["clauses"][-1]
        assert clause["version"] == last_clause["version"] + 1
        assert clause["source"] == "generated"
        assert _INPUTS["disclosing_party"] in clause["body"]

        # The regeneration prompt carries prior clause bodies, which must stay aliased.
        assert len(generator.prompts) == 1
        prompt = generator.prompts[0]
        assert "prior_clauses" in prompt
        for value in _INPUTS.values():
            assert value not in prompt
    finally:
        asyncio.run(_delete_test_organizations(settings.default_org_id))


def test_export_is_authorized_audited_and_renders_both_formats(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings, StubClauseGenerator())) as client:
            _register(client)
            draft = _create_draft(client)
            session_cookie = client.cookies.get(settings.session_cookie_name)

            client.cookies.clear()
            anonymous = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/export", json={"format": "docx"}
            )

            client.cookies.set(settings.session_cookie_name, session_cookie)
            docx = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/export", json={"format": "docx"}
            )
            pdf = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/export", json={"format": "pdf"}
            )
            unsupported = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/export", json={"format": "rtf"}
            )

        assert anonymous.status_code == 401
        assert docx.status_code == 200
        assert docx.content[:2] == b"PK"
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content[:5] == b"%PDF-"
        assert unsupported.status_code == 422

        exported = asyncio.run(_read_audit_actions(settings, "draft_export"))
        assert sorted(entry["format"] for entry in exported) == ["docx", "pdf"]
    finally:
        asyncio.run(_delete_test_organizations(settings.default_org_id))


def test_version_snapshots_are_listed_and_restorable(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings, StubClauseGenerator())) as client:
            _register(client)
            draft = _create_draft(client)
            clause = draft["clauses"][0]
            original_body = clause["body"]

            edited = client.put(
                f"/api/v1/drafting/drafts/{draft['id']}/clauses/{clause['id']}",
                json={"heading": "Definitions", "body": "Replaced clause text."},
            ).json()
            history = client.get(f"/api/v1/drafting/drafts/{draft['id']}/versions")
            restored = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/versions/1/restore"
            )
            missing = client.post(
                f"/api/v1/drafting/drafts/{draft['id']}/versions/99/restore"
            )
            final = client.get(f"/api/v1/drafting/drafts/{draft['id']}")

        assert edited["clauses"][0]["body"] == "Replaced clause text."
        assert history.status_code == 200
        assert [item["version"] for item in history.json()] == [1, 2]
        assert history.json()[0]["clause_count"] == len(draft["clauses"])
        assert restored.status_code == 200
        assert restored.json()["clauses"][0]["body"] == original_body
        assert restored.json()["version"] == 3
        assert missing.status_code == 404
        assert final.json()["clauses"][0]["body"] == original_body
    finally:
        asyncio.run(_delete_test_organizations(settings.default_org_id))


def test_organization_templates_are_authored_and_protect_builtins(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, default_org_id=f"test-{uuid4().hex}")

    try:
        with TestClient(_build_app(settings, StubClauseGenerator())) as client:
            _register(client)
            builtin_id = client.get("/api/v1/drafting/templates").json()[0]["id"]
            payload = {
                "name": "Vendor Data Processing Addendum",
                "document_type": "DPA",
                "input_schema": {"controller": {"label": "Controller", "required": True}},
                "clause_outline": [{"heading": "Processing Scope", "purpose": "Limit processing."}],
            }

            created = client.post("/api/v1/drafting/templates", json=payload)
            listed = client.get("/api/v1/drafting/templates")
            updated = client.put(
                f"/api/v1/drafting/templates/{created.json()['id']}",
                json={**payload, "document_type": "Data Processing Addendum"},
            )
            builtin_update = client.put(
                f"/api/v1/drafting/templates/{builtin_id}", json=payload
            )
            builtin_delete = client.delete(f"/api/v1/drafting/templates/{builtin_id}")
            invalid = client.post(
                "/api/v1/drafting/templates", json={**payload, "clause_outline": []}
            )
            removed = client.delete(f"/api/v1/drafting/templates/{created.json()['id']}")
            after_delete = client.get("/api/v1/drafting/templates")

        assert created.status_code == 201
        assert created.json()["slug"] == "vendor-data-processing-addendum"
        assert created.json()["is_builtin"] is False
        assert created.json()["id"] in [item["id"] for item in listed.json()]
        assert updated.json()["document_type"] == "Data Processing Addendum"
        assert builtin_update.status_code == 403
        assert builtin_delete.status_code == 403
        assert invalid.status_code == 422
        assert removed.status_code == 204
        assert created.json()["id"] not in [item["id"] for item in after_delete.json()]
    finally:
        asyncio.run(_delete_test_organizations(settings.default_org_id))
