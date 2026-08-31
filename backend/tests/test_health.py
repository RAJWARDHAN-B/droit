"""Tests for the API process health contract."""

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


def test_liveness_endpoint(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert settings.upload_directory.is_dir()