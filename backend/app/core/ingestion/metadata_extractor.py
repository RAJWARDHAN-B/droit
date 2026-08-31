"""Extract deterministic metadata from an ingested document."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def extract_document_metadata(
    file_path: str | Path,
    extracted_text: str,
) -> dict[str, Any]:
    """Return storage and text statistics suitable for document persistence."""
    path = Path(file_path)
    content = path.read_bytes()
    lines = extracted_text.splitlines()

    return {
        "extension": path.suffix.lower(),
        "file_size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "character_count": len(extracted_text),
        "word_count": len(extracted_text.split()),
        "line_count": len(lines),
    }