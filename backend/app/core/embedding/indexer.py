"""FastEmbed-backed Qdrant document indexing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models

from ...config import Settings


@dataclass(frozen=True)
class ChunkVector:
    point_id: UUID
    chunk_index: int
    text: str


class VectorIndexer(Protocol):
    async def index(
        self,
        *,
        document_id: UUID,
        organization_id: UUID,
        chunks: list[ChunkVector],
    ) -> None: ...

    async def delete(self, point_ids: list[UUID]) -> None: ...


class QdrantVectorIndexer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._collection = settings.qdrant_collection
        self._client: QdrantClient | None = None
        self._embedding: TextEmbedding | None = None

    async def index(
        self,
        *,
        document_id: UUID,
        organization_id: UUID,
        chunks: list[ChunkVector],
    ) -> None:
        if not chunks:
            raise ValueError("Cannot index a document without text chunks")
        await asyncio.to_thread(
            self._index_sync,
            document_id,
            organization_id,
            chunks,
        )

    async def delete(self, point_ids: list[UUID]) -> None:
        if point_ids:
            client, _ = self._dependencies()
            await asyncio.to_thread(
                client.delete,
                collection_name=self._collection,
                points_selector=models.PointIdsList(
                    points=[str(point_id) for point_id in point_ids]
                ),
                wait=True,
            )

    def _index_sync(
        self,
        document_id: UUID,
        organization_id: UUID,
        chunks: list[ChunkVector],
    ) -> None:
        client, embedding = self._dependencies()
        vectors = [vector.tolist() for vector in embedding.embed(
            [chunk.text for chunk in chunks]
        )]
        if not client.collection_exists(self._collection):
            client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=len(vectors[0]), distance=models.Distance.COSINE
                ),
            )
        client.upsert(
            collection_name=self._collection,
            points=[
                models.PointStruct(
                    id=str(chunk.point_id),
                    vector=vector,
                    payload={
                        "document_id": str(document_id),
                        "organization_id": str(organization_id),
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
            wait=True,
        )

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