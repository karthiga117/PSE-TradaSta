"""Retrieval abstraction for knowledge-search queries."""

from __future__ import annotations

from typing import Any

from app.application.knowledge.embedding import EmbeddingProvider
from app.application.knowledge.vector_store import VectorStore
from app.domain.knowledge.models import RetrievalRequest, RetrievalResult


class KnowledgeRetriever:
    """Generate query embeddings and retrieve relevant knowledge chunks."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        *,
        default_top_k: int = 5,
        default_min_score: float = 0.0,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.default_top_k = max(1, default_top_k)
        self.default_min_score = max(0.0, default_min_score)

    def retrieve(self, request: RetrievalRequest | dict[str, Any]) -> list[RetrievalResult]:
        """Search for relevant chunks using the configured vector store."""
        normalized = (
            request
            if isinstance(request, RetrievalRequest)
            else RetrievalRequest.from_mapping(request)
        )
        if normalized.top_k > 10:
            normalized = RetrievalRequest(
                query=normalized.query,
                top_k=10,
                category=normalized.category,
                source=normalized.source,
                tags=normalized.tags,
                minimum_score=normalized.minimum_score,
                max_top_k=normalized.max_top_k,
            )

        query_embedding = self.embedding_provider.embed_text(normalized.query)
        matches = self.vector_store.search(
            query_embedding,
            top_k=normalized.top_k,
            category=normalized.category,
            source=normalized.source,
            tags=normalized.tags,
            minimum_score=normalized.minimum_score,
        )

        results: list[RetrievalResult] = []
        for chunk, _embedding, score in matches:
            metadata = dict(chunk.metadata)
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    score=float(score),
                    document_id=chunk.document_id,
                    title=str(metadata.get("title") or "Untitled document"),
                    source=str(metadata.get("source") or "unknown"),
                    section=str(metadata.get("section")) if metadata.get("section") else None,
                    metadata=metadata,
                )
            )
        return results

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        category: str | None = None,
        source: str | None = None,
        tags: list[str] | None = None,
        minimum_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """Convenience wrapper for a direct string query."""
        request = RetrievalRequest(
            query=query,
            top_k=top_k,
            category=category,
            source=source,
            tags=tags,
            minimum_score=minimum_score,
            max_top_k=self.default_top_k,
        )
        return self.retrieve(request)


__all__ = ["KnowledgeRetriever"]
