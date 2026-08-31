"""Tests for document text extraction."""

import pytest

from backend.app.core.ingestion import extract_document_metadata, load_document


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


def test_extracts_deterministic_file_and_text_metadata(tmp_path) -> None:
    document = tmp_path / "agreement.TXT"
    document.write_text("Mutual NDA\nTwo parties", encoding="utf-8")

    metadata = extract_document_metadata(document, "Mutual NDA\nTwo parties")

    assert metadata["extension"] == ".txt"
    assert metadata["file_size_bytes"] == 22
    assert metadata["character_count"] == 22
    assert metadata["word_count"] == 4
    assert metadata["line_count"] == 2
    assert metadata["sha256"] == (
        "83e8159424a5dec83840ed029f644dae2db2345744624eaa346d72bd732eb00e"
    )