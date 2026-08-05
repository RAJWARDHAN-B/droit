"""
droit/retrieval/retriever.py
-----------------------------
Stage 5: Retrieval + Cross-Encoder Reranking

Two-stage retrieval pipeline:

  Stage 1 — Vector Search
    ChromaDB similarity_search() returns the top-k semantically similar chunks
    (cheap approximate nearest-neighbour lookup).

  Stage 2 — Cross-Encoder Reranking
    A BAAI/bge-reranker-v2-m3 cross-encoder scores each (query, chunk) pair
    with higher precision, then we keep only the top-n reranked chunks to pass
    to the LLM. This dramatically reduces hallucination risk.
"""

from __future__ import annotations

import logging

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from droit.config import (
    RERANKER_MAX_LENGTH,
    RERANKER_MODEL_NAME,
    RERANK_TOP_K,
    RETRIEVAL_TOP_K,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cross-encoder singleton — loaded once per process
# ---------------------------------------------------------------------------
_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info("Loading cross-encoder '%s' …", RERANKER_MODEL_NAME)
        _reranker = CrossEncoder(RERANKER_MODEL_NAME, max_length=RERANKER_MAX_LENGTH)
        logger.info("Cross-encoder ready.")
    return _reranker


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve_and_rerank(
    query: str,
    vectorstore: Chroma,
    top_k_retrieval: int = RETRIEVAL_TOP_K,
    top_k_rerank: int = RERANK_TOP_K,
) -> list[Document]:
    """
    Run a two-stage retrieval: vector search → cross-encoder reranking.

    Parameters
    ----------
    query : str
        Natural-language question from the user.
    vectorstore : Chroma
        Live ChromaDB vectorstore (from ``indexer.build_index()`` or ``load_index()``).
    top_k_retrieval : int
        Number of candidate chunks fetched from ChromaDB in Stage 1.
    top_k_rerank : int
        Number of final chunks returned after Stage 2 reranking.

    Returns
    -------
    list[Document]
        Top reranked LangChain Documents, ordered by relevance (best first).
    """
    # --- Stage 1: Vector Search ---
    candidates: list[Document] = vectorstore.similarity_search(
        query, k=top_k_retrieval
    )
    logger.info(
        "Stage 1 | Retrieved %d candidate chunks for query: '%s'",
        len(candidates),
        query,
    )

    if not candidates:
        logger.warning("No candidates retrieved from vector store.")
        return []

    # --- Stage 2: Cross-Encoder Reranking ---
    reranker = _get_reranker()
    pairs = [[query, doc.page_content] for doc in candidates]
    scores = reranker.predict(pairs)

    scored = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    reranked = [doc for doc, _ in scored[:top_k_rerank]]

    logger.info(
        "Stage 2 | Reranked to top %d chunks. "
        "Best score: %.4f | Worst score: %.4f",
        len(reranked),
        scored[0][1],
        scored[min(top_k_rerank - 1, len(scored) - 1)][1],
    )

    # Log the selected chunks for debugging
    for rank, (doc, score) in enumerate(scored[:top_k_rerank], start=1):
        logger.debug(
            "  Rank %d | score=%.4f | chunk_id=%s",
            rank,
            score,
            doc.metadata.get("chunk_id", "n/a"),
        )

    return reranked
