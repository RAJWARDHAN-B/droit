"""Tests for document text extraction."""

import pytest

from backend.app.core.ingestion import load_document


def test_loads_utf8_text(tmp_path) -> None:
    document = tmp_path / "agreement.txt"
    document.write_text("Mutual non-disclosure agreement", encoding="utf-8")

    assert load_document(document) == "Mutual non-disclosure agreement"


def test_csv_rows_retain_header_context(tmp_path) -> None:
    document = tmp_path / "obligations.csv"
    document.write_text(
        "Party,Obligation,Due Date\nSupplier,Deliver report,2026-09-30\n",
        encoding="utf-8",
    )

    extracted = load_document(document)

    assert "Table: obligations" in extracted
    assert "Party: Supplier" in extracted
    assert "Obligation: Deliver report" in extracted
    assert "Due Date: 2026-09-30" in extracted


def test_rejects_unsupported_file_type(tmp_path) -> None:
    document = tmp_path / "agreement.md"
    document.write_text("text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_document(document)