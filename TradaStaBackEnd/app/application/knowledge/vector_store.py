"""Vector store abstraction and in-memory implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from math import sqrt

from app.domain.knowledge.models import KnowledgeChunk, KnowledgeEmbedding


class VectorStore(ABC):
    """Storage and search interface for chunk embeddings."""

    @abstractmethod
    def add(self, chunk: KnowledgeChunk, embedding: KnowledgeEmbedding) -> None:
        """Store one chunk embedding."""

    @abstractmethod
    def add_batch(self, items: list[tuple[KnowledgeChunk, KnowledgeEmbedding]]) -> None:
        """Store multiple chunk embeddings."""

    @abstractmethod
    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 5,
        category: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        minimum_score: float = 0.0,
    ) -> list[tuple[KnowledgeChunk, KnowledgeEmbedding, float]]:
        """Return the most relevant chunk embeddings in descending score order."""

    @abstractmethod
    def delete(self, chunk_id: str) -> None:
        """Delete a stored chunk and its embedding."""

    @abstractmethod
    def update(self, chunk: KnowledgeChunk, embedding: KnowledgeEmbedding) -> None:
        """Replace an existing chunk embedding."""


class InMemoryVectorStore(VectorStore):
    """Simple in-memory vector store for local development and tests."""

    def __init__(self) -> None:
        self._chunks: dict[str, KnowledgeChunk] = {}
        self._embeddings: dict[str, KnowledgeEmbedding] = {}
        self._document_hashes: set[str] = set()

    def add(self, chunk: KnowledgeChunk, embedding: KnowledgeEmbedding) -> None:
        self._chunks[chunk.id] = chunk
        self._embeddings[chunk.id] = embedding

    def add_batch(self, items: list[tuple[KnowledgeChunk, KnowledgeEmbedding]]) -> None:
        for chunk, embedding in items:
            self.add(chunk, embedding)

    def search(
        self,
        query_embedding: Sequence[float],
        *,
        top_k: int = 5,
        category: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        minimum_score: float = 0.0,
    ) -> list[tuple[KnowledgeChunk, KnowledgeEmbedding, float]]:
        matches: list[tuple[KnowledgeChunk, KnowledgeEmbedding, float]] = []
        query_vector = [float(value) for value in query_embedding]
        normalized_tags = {str(tag).lower() for tag in (tags or [])}
        for chunk in self._chunks.values():
            metadata = chunk.metadata
            stored_category = str(metadata.get("category", "")).lower()
            if category is not None and stored_category != str(category).lower():
                continue
            stored_source = str(metadata.get("source", "")).lower()
            if source is not None and stored_source != str(source).lower():
                continue
            stored_tags = {
                str(tag).lower()
                for tag in metadata.get("tags", [])
                if isinstance(metadata.get("tags"), list)
            }
            if normalized_tags and not normalized_tags.issubset(stored_tags):
                continue

            embedding = self._embeddings.get(chunk.id)
            if embedding is None:
                continue
            score = self._cosine_similarity(query_vector, embedding.embedding)
            if score < minimum_score:
                continue
            matches.append((chunk, embedding, score))

        matches.sort(key=lambda item: (-item[2], item[0].id))
        return matches[:top_k]

    def delete(self, chunk_id: str) -> None:
        self._chunks.pop(chunk_id, None)
        self._embeddings.pop(chunk_id, None)

    def update(self, chunk: KnowledgeChunk, embedding: KnowledgeEmbedding) -> None:
        self._chunks[chunk.id] = chunk
        self._embeddings[chunk.id] = embedding

    def register_document_hash(self, document_hash: str) -> None:
        self._document_hashes.add(document_hash)

    def has_document_hash(self, document_hash: str) -> bool:
        return document_hash in self._document_hashes

    def is_empty(self) -> bool:
        return not self._chunks

    @staticmethod
    def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
        left_norm = sqrt(sum(value * value for value in left))
        right_norm = sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        denominator = left_norm * right_norm
        if denominator == 0:
            return 0.0
        numerator = sum(l_value * r_value for l_value, r_value in zip(left, right, strict=True))
        return numerator / denominator


__all__ = ["InMemoryVectorStore", "VectorStore"]
