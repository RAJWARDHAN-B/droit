"""Tests for hybrid document retrieval ranking."""

from types import SimpleNamespace
from uuid import UUID

import pytest

from backend.app.core.retrieval.retriever import (
    HybridRetriever,
    RetrievedChunk,
    rank_hybrid_chunks,
    reciprocal_rank_fusion,
)


CHUNK_ONE = UUID("00000000-0000-0000-0000-000000000001")
CHUNK_TWO = UUID("00000000-0000-0000-0000-000000000002")
DOCUMENT = UUID("10000000-0000-0000-0000-000000000001")


def test_rrf_combines_weighted_rankings() -> None:
    scores = reciprocal_rank_fusion(
        [(2.0, [CHUNK_ONE, CHUNK_TWO]), (1.0, [CHUNK_TWO])],
        rank_constant=10,
    )

    assert scores[CHUNK_ONE] == pytest.approx(2 / 11)
    assert scores[CHUNK_TWO] == pytest.approx(2 / 12 + 1 / 11)


def test_hybrid_ranking_rewards_vector_and_lexical_agreement() -> None:
    candidates = [
        RetrievedChunk(CHUNK_ONE, DOCUMENT, 0, "Confidential information survives"),
        RetrievedChunk(CHUNK_TWO, DOCUMENT, 1, "Termination requires thirty days"),
    ]

    ranked = rank_hybrid_chunks(
        "termination notice",
        candidates,
        [CHUNK_TWO, CHUNK_ONE],
        limit=2,
    )

    assert [chunk.chunk_id for chunk in ranked] == [CHUNK_TWO, CHUNK_ONE]
    assert ranked[0].score > ranked[1].score


def test_single_candidate_still_matches_despite_negative_bm25_idf() -> None:
    candidates = [
        RetrievedChunk(CHUNK_ONE, DOCUMENT, 0, "Either party may terminate the agreement")
    ]

    ranked = rank_hybrid_chunks("terminate agreement", candidates, [], limit=5)

    assert [chunk.chunk_id for chunk in ranked] == [CHUNK_ONE]


def test_hybrid_ranking_excludes_chunks_without_query_terms() -> None:
    candidates = [
        RetrievedChunk(CHUNK_ONE, DOCUMENT, 0, "Governing law is Delaware"),
    ]

    assert rank_hybrid_chunks("payment schedule", candidates, [], limit=5) == []


def test_hybrid_ranking_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        rank_hybrid_chunks("  ", [], [], limit=2)


@pytest.mark.asyncio
async def test_hybrid_retriever_applies_cross_encoder_ordering() -> None:
    class StubVectorSearcher:
        async def search(self, *args, **kwargs):
            return [CHUNK_ONE, CHUNK_TWO]

    class ReversingReranker:
        async def rerank(self, query, chunks):
            return list(reversed(chunks))

    class StubScalars:
        def all(self):
            return [
                SimpleNamespace(
                    id=CHUNK_ONE,
                    document_id=DOCUMENT,
                    chunk_index=0,
                    text="Termination requires notice",
                ),
                SimpleNamespace(
                    id=CHUNK_TWO,
                    document_id=DOCUMENT,
                    chunk_index=1,
                    text="Termination is immediate",
                ),
            ]

    class StubSession:
        async def execute(self, statement):
            return SimpleNamespace(scalars=lambda: StubScalars())

    settings = SimpleNamespace(
        retrieval_candidate_limit=30,
        retrieval_reranker_candidate_limit=12,
        retrieval_vector_weight=1.0,
        retrieval_bm25_weight=1.0,
        retrieval_rrf_k=60,
    )
    retriever = HybridRetriever(
        StubVectorSearcher(), settings, reranker=ReversingReranker()
    )

    ranked = await retriever.retrieve(
        StubSession(),
        "termination",
        organization_id=DOCUMENT,
        limit=2,
    )

    assert [chunk.chunk_id for chunk in ranked] == [CHUNK_TWO, CHUNK_ONE]