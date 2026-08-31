"""Tests for legal text chunking constraints."""

import pytest

from backend.app.core.chunking import split_text


def test_split_text_respects_configured_size() -> None:
    chunks = split_text("Clause one. " * 30, chunk_size=80, chunk_overlap=10)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 80 for chunk in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (100, -1), (100, 100)],
)
def test_split_text_rejects_invalid_configuration(
    chunk_size: int, chunk_overlap: int
) -> None:
    with pytest.raises(ValueError):
        split_text(
            "Contract text", chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )