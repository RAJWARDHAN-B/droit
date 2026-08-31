"""Organization-scoped cosine and BM25 hybrid retrieval."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, replace
from typing import Protocol
from uuid import UUID

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import Settings
from ...models import Document, DocumentChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    score: float = 0.0


class VectorSearcher(Protocol):
    async def search(
        self,
        query: str,
        *,
        organization_id: UUID,
        document_id: UUID | None,
        limit: int,
    ) -> list[UUID]: ...


class ChunkReranker(Protocol):
    async def rerank(
        self, query: str, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]: ...


def reciprocal_rank_fusion(
    rankings: list[tuple[float, list[UUID]]],
    *,
    rank_constant: int = 60,
) -> dict[UUID, float]:
    if rank_constant < 0:
        raise ValueError("RRF rank constant cannot be negative")

    scores: dict[UUID, float] = {}
    for weight, ranking in rankings:
        if weight < 0:
            raise ValueError("RRF source weights cannot be negative")
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (
                rank_constant + rank
            )
    return scores


def rank_hybrid_chunks(
    query: str,
    candidates: list[RetrievedChunk],
    vector_ranking: list[UUID],
    *,
    limit: int,
    vector_weight: float = 1.0,
    bm25_weight: float = 1.0,
    rank_constant: int = 60,
) -> list[RetrievedChunk]:
    terms = _tokenize(query)
    if not terms:
        raise ValueError("Retrieval query cannot be blank")
    if limit < 1:
        raise ValueError("Retrieval limit must be positive")
    if not candidates:
        return []

    candidate_tokens = [_tokenize(chunk.text) for chunk in candidates]
    bm25 = BM25Okapi(candidate_tokens)
    lexical_scores = bm25.get_scores(terms)
    query_terms = set(terms)
    # BM25 scores go negative on small corpora, so term overlap decides eligibility.
    bm25_ranking = [
        candidates[index].chunk_id
        for index in sorted(
            range(len(candidates)),
            key=lambda index: (-lexical_scores[index], candidates[index].chunk_index),
        )
        if query_terms.intersection(candidate_tokens[index])
    ]
    candidate_ids = {chunk.chunk_id for chunk in candidates}
    filtered_vector_ranking = [
        chunk_id for chunk_id in vector_ranking if chunk_id in candidate_ids
    ]
    scores = reciprocal_rank_fusion(
        [
            (vector_weight, filtered_vector_ranking),
            (bm25_weight, bm25_ranking),
        ],
        rank_constant=rank_constant,
    )
    ranked = sorted(
        (chunk for chunk in candidates if chunk.chunk_id in scores),
        key=lambda chunk: (-scores[chunk.chunk_id], str(chunk.chunk_id)),
    )
    return [replace(chunk, score=scores[chunk.chunk_id]) for chunk in ranked[:limit]]


class HybridRetriever:
    def __init__(
        self,
        vector_searcher: VectorSearcher,
        settings: Settings,
        reranker: ChunkReranker | None = None,
    ) -> None:
        self._vector_searcher = vector_searcher
        self._settings = settings
        self._reranker = reranker

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        *,
        organization_id: UUID,
        document_id: UUID | None = None,
        limit: int = 8,
    ) -> list[RetrievedChunk]:
        statement = (
            select(DocumentChunk)
            .join(Document)
            .where(Document.organization_id == organization_id)
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        )
        if document_id is not None:
            statement = statement.where(DocumentChunk.document_id == document_id)
        result = await session.execute(statement)
        candidates = [
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            for chunk in result.scalars().all()
        ]
        vector_ranking = await self._vector_searcher.search(
            query,
            organization_id=organization_id,
            document_id=document_id,
            limit=self._settings.retrieval_candidate_limit,
        )
        ranked = rank_hybrid_chunks(
            query,
            candidates,
            vector_ranking,
            limit=max(limit, self._settings.retrieval_reranker_candidate_limit),
            vector_weight=self._settings.retrieval_vector_weight,
            bm25_weight=self._settings.retrieval_bm25_weight,
            rank_constant=self._settings.retrieval_rrf_k,
        )
        if self._reranker is not None and ranked:
            ranked = await self._reranker.rerank(query, ranked)
        return ranked[:limit]


class CrossEncoderReranker:
    """Lazily score query/chunk pairs with a sentence-transformers model."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: object | None = None

    async def rerank(
        self, query: str, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        return await asyncio.to_thread(self._rerank_sync, query, chunks)

    def _rerank_sync(
        self, query: str, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        scores = self._model.predict([(query, chunk.text) for chunk in chunks])  # type: ignore[attr-defined]
        rescored = [
            replace(chunk, score=float(score))
            for chunk, score in zip(chunks, scores, strict=True)
        ]
        return sorted(
            rescored,
            key=lambda chunk: (-chunk.score, str(chunk.chunk_id)),
        )


class QdrantVectorSearcher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._collection = settings.qdrant_collection
        self._client: QdrantClient | None = None
        self._embedding: TextEmbedding | None = None

    async def search(
        self,
        query: str,
        *,
        organization_id: UUID,
        document_id: UUID | None,
        limit: int,
    ) -> list[UUID]:
        return await asyncio.to_thread(
            self._search_sync,
            query,
            organization_id,
            document_id,
            limit,
        )

    def _search_sync(
        self,
        query: str,
        organization_id: UUID,
        document_id: UUID | None,
        limit: int,
    ) -> list[UUID]:
        client, embedding = self._dependencies()
        vector = next(iter(embedding.embed([query]))).tolist()
        conditions = [
            models.FieldCondition(
                key="organization_id",
                match=models.MatchValue(value=str(organization_id)),
            )
        ]
        if document_id is not None:
            conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=str(document_id)),
                )
            )
        response = client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=models.Filter(must=conditions),
            limit=limit,
            with_payload=False,
            with_vectors=False,
        )
        return [UUID(str(point.id)) for point in response.points]

    def _dependencies(self) -> tuple[QdrantClient, TextEmbedding]:
        if self._client is None:
            self._client = QdrantClient(url=self._settings.qdrant_url)
        if self._embedding is None:
            self._embedding = TextEmbedding(
                model_name=self._settings.embedding_model,
                cache_dir=str(self._settings.storage_root / "models"),
                lazy_load=True,
            )
        return self._client, self._embedding


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\w'-]+", text.casefold())