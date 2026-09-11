"""Knowledge retrieval API for the TradaSta RAG layer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.application.knowledge.context_builder import RagContextBuilder
from app.application.knowledge.embedding import DeterministicEmbeddingProvider
from app.application.knowledge.ingestion import KnowledgeIngestionService
from app.application.knowledge.retriever import KnowledgeRetriever
from app.application.knowledge.vector_store import InMemoryVectorStore
from app.core.config import Settings, get_settings
from app.domain.knowledge.models import (
    KnowledgeCategory,
    KnowledgeDocument,
    KnowledgeSourceType,
    RetrievalRequest,
)

router = APIRouter(tags=["knowledge-base"])


def get_knowledge_store() -> InMemoryVectorStore:
    """Provide a process-local vector store for knowledge retrieval."""
    return _DEFAULT_KNOWLEDGE_STORE


_DEFAULT_KNOWLEDGE_STORE = InMemoryVectorStore()


def ensure_default_dataset() -> InMemoryVectorStore:
    """Initialize a compact default dataset for local development/testing."""
    if not _DEFAULT_KNOWLEDGE_STORE.is_empty():
        return _DEFAULT_KNOWLEDGE_STORE

    dataset_directory = Path(__file__).resolve().parents[2] / "data" / "knowledge"
    if not dataset_directory.exists():
        return _DEFAULT_KNOWLEDGE_STORE

    service = KnowledgeIngestionService(
        _DEFAULT_KNOWLEDGE_STORE,
        DeterministicEmbeddingProvider(),
        chunk_size=get_settings().knowledge_chunk_size,
        chunk_overlap=get_settings().knowledge_chunk_overlap,
    )
    service.ingest_directory(dataset_directory)
    return _DEFAULT_KNOWLEDGE_STORE


class KnowledgeSearchRequest(BaseModel):
    """Request model for semantic knowledge search."""

    query: str
    top_k: int = 5
    category: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    minimum_score: float = 0.0

    model_config = ConfigDict(use_enum_values=True)


class KnowledgeSearchResult(BaseModel):
    """Returned chunk result for knowledge lookup."""

    chunk_id: str
    content: str
    score: float
    document_id: str
    title: str
    source: str
    section: str | None = None
    metadata: dict[str, Any] = {}


class KnowledgeSearchResponse(BaseModel):
    """Stable response type for retrieval results."""

    query: str
    results: list[KnowledgeSearchResult] = []


class KnowledgeIngestRequest(BaseModel):
    """Document ingestion payload."""

    title: str
    content: str
    source: str
    category: str = KnowledgeCategory.TECHNICAL_ANALYSIS.value
    source_type: str = KnowledgeSourceType.MARKDOWN.value
    tags: list[str] = []
    version: str = "1.0"


class KnowledgeIngestResponse(BaseModel):
    """Document ingestion summary."""

    document_id: str
    title: str
    chunks_created: int
    embeddings_created: int
    status: str
    content_hash: str | None = None


@router.post("/knowledge/search")
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    settings: Annotated[Settings, Depends(lambda: get_settings())],
) -> KnowledgeSearchResponse:
    """Search the knowledge base for relevant trading context without invoking an LLM."""
    store = ensure_default_dataset()
    retriever = KnowledgeRetriever(
        store,
        DeterministicEmbeddingProvider(),
        default_top_k=settings.knowledge_max_top_k,
        default_min_score=settings.knowledge_min_score,
    )
    request = RetrievalRequest.from_mapping(
        {
            "query": payload.query,
            "top_k": payload.top_k,
            "category": payload.category,
            "source": payload.source,
            "tags": payload.tags,
            "minimum_score": payload.minimum_score,
            "max_top_k": settings.knowledge_max_top_k,
        }
    )
    results = retriever.retrieve(request)
    return KnowledgeSearchResponse(
        query=payload.query,
        results=[
            KnowledgeSearchResult(
                chunk_id=result.chunk_id,
                content=result.content,
                score=result.score,
                document_id=result.document_id,
                title=result.title,
                source=result.source,
                section=result.section,
                metadata=result.metadata,
            )
            for result in results
        ],
    )


@router.post("/knowledge/ingest")
async def ingest_knowledge(
    payload: KnowledgeIngestRequest,
    settings: Annotated[Settings, Depends(lambda: get_settings())],
) -> KnowledgeIngestResponse:
    """Ingest a document into the local knowledge base."""
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")

    document = KnowledgeDocument(
        title=payload.title,
        content=payload.content,
        source=payload.source,
        category=payload.category,
        source_type=payload.source_type,
        tags=payload.tags,
        version=payload.version,
    )
    store = ensure_default_dataset()
    ingestor = KnowledgeIngestionService(
        store,
        DeterministicEmbeddingProvider(),
        chunk_size=settings.knowledge_chunk_size,
        chunk_overlap=settings.knowledge_chunk_overlap,
    )
    result = ingestor.ingest_document(document)
    return KnowledgeIngestResponse(
        document_id=result.document_id,
        title=result.title,
        chunks_created=result.chunks_created,
        embeddings_created=result.embeddings_created,
        status=result.status,
        content_hash=result.content_hash,
    )


@router.get("/knowledge/context")
async def build_knowledge_context(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=10),
    *,
    settings: Annotated[Settings, Depends(lambda: get_settings())],
) -> dict[str, object]:
    """Build a compact retrieval context for future orchestration phases."""
    store = ensure_default_dataset()
    retriever = KnowledgeRetriever(
        store,
        DeterministicEmbeddingProvider(),
        default_top_k=settings.knowledge_max_top_k,
        default_min_score=settings.knowledge_min_score,
    )
    results = retriever.search(
        query,
        top_k=top_k,
        minimum_score=settings.knowledge_min_score,
    )
    context = RagContextBuilder(
        max_context_chunks=top_k,
        max_context_characters=2000,
    ).build(query, results)
    return {
        "query": context.query,
        "sources": context.sources,
        "chunks": context.chunks,
        "total_results": context.total_results,
        "context_text": context.context_text,
    }


__all__ = ["router"]
