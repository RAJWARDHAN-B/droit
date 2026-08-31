"""Tests for hybrid document retrieval ranking."""

from uuid import UUID

import pytest

from backend.app.core.retrieval.retriever import (
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


def test_hybrid_ranking_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="cannot be blank"):
        rank_hybrid_chunks("  ", [], [], limit=2)