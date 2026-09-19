"""Tests for the API process health contract."""

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.database import get_session
from backend.app.main import create_app


def test_liveness_endpoint(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert settings.upload_directory.is_dir()


def test_readiness_checks_database(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)
    app = create_app(settings)

    class ReadySession:
        async def execute(self, _statement) -> None:
            return None

    async def override_session():
        yield ReadySession()

    app.dependency_overrides[get_session] = override_session

    class HealthyResponse:
        def raise_for_status(self) -> None:
            return None

    class HealthyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, _url):
            return HealthyResponse()

    app.state.health_client = HealthyClient()

    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok", "qdrant": "ok"}