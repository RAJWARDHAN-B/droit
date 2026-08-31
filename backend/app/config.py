"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for the Droit API."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="DROIT_",
        extra="ignore",
    )

    app_name: str = "Droit API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://droit:droit_secret@localhost:5432/droit_db"
    )
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "droit_legal_documents"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    storage_root: Path = PROJECT_ROOT / "storage"
    default_org_id: str = "org_default"
    max_upload_bytes: int = 25 * 1024 * 1024
    pii_encryption_key: SecretStr | None = None
    chunk_size: int = 800
    chunk_overlap: int = 150
    retrieval_candidate_limit: int = 30
    retrieval_vector_weight: float = 1.0
    retrieval_bm25_weight: float = 1.0
    retrieval_rrf_k: int = 60

    @property
    def upload_directory(self) -> Path:
        """Return the local upload directory for the single organization."""
        return self.storage_root / "uploads" / self.default_org_id


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide immutable settings instance."""
    return Settings()