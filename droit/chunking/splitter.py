"""
droit/chunking/splitter.py
---------------------------
Stage 3: Text Splitting

Splits raw document text into overlapping chunks and wraps each chunk
as a LangChain ``Document`` object carrying inherited document-level metadata.

Each chunk also gets two chunk-specific fields injected into its metadata:
  - chunk_id    : "{source_file}_chunk_{index}"  (unique, traceable identifier)
  - chunk_index : integer position within the document
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from droit.config import CHUNK_OVERLAP, CHUNK_SEPARATORS, CHUNK_SIZE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level splitter singleton — instantiated once, reused across calls
# ---------------------------------------------------------------------------
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=CHUNK_SEPARATORS,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def split_document(
    text: str,
    global_metadata: dict[str, Any],
) -> list[Document]:
    """
    Split raw text into overlapping chunks and attach metadata.

    Parameters
    ----------
    text : str
        Full raw text of the document.
    global_metadata : dict
        Document-level metadata produced by ``metadata_extractor.extract_metadata()``.
        Copied into every chunk so vector-store queries can filter on it.

    Returns
    -------
    list[Document]
        Ordered list of LangChain Document objects, one per chunk.
    """
    raw_chunks = _splitter.split_text(text)
    documents: list[Document] = []

    source = global_metadata.get("source_file", "unknown")

    for idx, chunk_text in enumerate(raw_chunks):
        # Copy so each chunk holds an independent metadata dict
        chunk_metadata = global_metadata.copy()
        chunk_metadata["chunk_id"]    = f"{source}_chunk_{idx}"
        chunk_metadata["chunk_index"] = idx

        documents.append(
            Document(page_content=chunk_text, metadata=chunk_metadata)
        )

    logger.info(
        "Split '%s' into %d chunks (size=%d, overlap=%d).",
        source,
        len(documents),
        CHUNK_SIZE,
        CHUNK_OVERLAP,
    )
    return documents
