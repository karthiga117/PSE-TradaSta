"""Tests for the RAG knowledge-base layer."""

from __future__ import annotations

from app.application.knowledge.embedding import DeterministicEmbeddingProvider
from app.application.knowledge.ingestion import KnowledgeIngestionService
from app.application.knowledge.retriever import KnowledgeRetriever
from app.application.knowledge.vector_store import InMemoryVectorStore
from app.domain.knowledge.models import KnowledgeCategory, KnowledgeDocument


def test_knowledge_ingestion_creates_embeddings() -> None:
    store = InMemoryVectorStore()
    service = KnowledgeIngestionService(
        store,
        DeterministicEmbeddingProvider(),
        chunk_size=200,
        chunk_overlap=20,
    )

    document = KnowledgeDocument(
        title="RSI Guide",
        content="The Relative Strength Index measures momentum and identifies overbought conditions.",
        source="rsi.md",
        category=KnowledgeCategory.TECHNICAL_ANALYSIS,
        tags=["rsi", "momentum"],
    )

    result = service.ingest_document(document)

    assert result.status == "COMPLETED"
    assert result.chunks_created == 1
    assert result.embeddings_created == 1
    assert store.is_empty() is False


def test_knowledge_retriever_filters_by_category() -> None:
    store = InMemoryVectorStore()
    service = KnowledgeIngestionService(
        store,
        DeterministicEmbeddingProvider(),
        chunk_size=200,
        chunk_overlap=20,
    )
    service.ingest_document(
        KnowledgeDocument(
            title="Risk Basics",
            content="Risk management means limiting losses and sizing positions carefully.",
            source="risk.md",
            category=KnowledgeCategory.RISK_MANAGEMENT,
            tags=["risk"],
        )
    )
    service.ingest_document(
        KnowledgeDocument(
            title="Trend Basics",
            content="Trend analysis helps identify momentum and direction in the market.",
            source="trend.md",
            category=KnowledgeCategory.TECHNICAL_ANALYSIS,
            tags=["trend"],
        )
    )

    retriever = KnowledgeRetriever(store, DeterministicEmbeddingProvider())
    results = retriever.search(
        "How should position sizing be calculated?",
        top_k=5,
        category=KnowledgeCategory.RISK_MANAGEMENT.value,
    )

    assert len(results) >= 1
    assert all(result.source == "risk.md" for result in results)
