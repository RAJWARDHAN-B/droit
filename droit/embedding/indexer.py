"""
droit/embedding/indexer.py
---------------------------
Stage 4: Embedding + Vector Store Indexing

Responsibilities:
  1. Load (or reuse) a HuggingFace sentence-transformer embedding model.
  2. Create or load a persistent ChromaDB collection on disk.
  3. Provide a function to add a batch of LangChain Documents to the store.
  4. Return the live vectorstore handle for downstream retrieval.

ChromaDB is configured for disk persistence so indexed documents survive
process restarts — no re-indexing required on every run.
"""

from __future__ import annotations

import logging

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from droit.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL_NAME,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton for the embedding model
# Loaded once; subsequent calls to build_index() / load_index() reuse it.
# ---------------------------------------------------------------------------
_embeddings: HuggingFaceEmbeddings | None = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info(
            "Loading embedding model '%s' on device '%s' …",
            EMBEDDING_MODEL_NAME,
            EMBEDDING_DEVICE,
        )
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": EMBEDDING_DEVICE},
        )
        logger.info("Embedding model ready.")
    return _embeddings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_index(documents: list[Document]) -> Chroma:
    """
    Embed and index a list of LangChain Documents into ChromaDB.

    Creates a new collection (or overwrites an existing one with the same name).
    The index is persisted to ``CHROMA_PERSIST_DIR`` automatically.

    Parameters
    ----------
    documents : list[Document]
        Chunked documents produced by ``chunking.splitter.split_document()``.

    Returns
    -------
    Chroma
        A live, queryable LangChain Chroma vectorstore.
    """
    logger.info(
        "Indexing %d chunks into ChromaDB collection '%s' at '%s' …",
        len(documents),
        CHROMA_COLLECTION_NAME,
        CHROMA_PERSIST_DIR,
    )
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=_get_embeddings(),
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    logger.info(
        "Indexed %d chunks successfully.",
        vectorstore._collection.count(),
    )
    return vectorstore


def load_index() -> Chroma:
    """
    Load an existing ChromaDB index from disk without re-indexing.

    Use this when the documents have already been indexed in a previous run.

    Returns
    -------
    Chroma
        A live, queryable LangChain Chroma vectorstore.

    Raises
    ------
    RuntimeError
        If no persisted index is found at ``CHROMA_PERSIST_DIR``.
    """
    logger.info(
        "Loading existing ChromaDB index from '%s' …", CHROMA_PERSIST_DIR
    )
    try:
        vectorstore = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=CHROMA_PERSIST_DIR,
        )
        count = vectorstore._collection.count()
        if count == 0:
            raise RuntimeError(
                f"ChromaDB collection '{CHROMA_COLLECTION_NAME}' exists but is empty. "
                "Run build_index() first."
            )
        logger.info("Loaded index with %d chunks.", count)
        return vectorstore
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load ChromaDB index from '{CHROMA_PERSIST_DIR}': {exc}"
        ) from exc
