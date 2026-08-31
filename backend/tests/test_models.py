"""Schema contract tests for Phase 1 persistence models."""

from backend.app.models import Base


def test_phase_one_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "document_chunks",
        "documents",
        "organizations",
        "pii_mappings",
        "processing_jobs",
        "users",
    }


def test_pii_original_is_only_stored_in_encrypted_column() -> None:
    columns = set(Base.metadata.tables["pii_mappings"].columns.keys())

    assert "original_value_encrypted" in columns
    assert "original_value" not in columns