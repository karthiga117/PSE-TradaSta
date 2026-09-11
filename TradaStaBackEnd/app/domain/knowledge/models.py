"""Knowledge-domain models for retrieval augmented generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256


class KnowledgeSourceType(StrEnum):
    """Supported source types for local knowledge documents."""

    MARKDOWN = "MARKDOWN"
    TEXT = "TEXT"
    PDF = "PDF"
    URL = "URL"


class KnowledgeCategory(StrEnum):
    """Controlled categories for knowledge retrieval."""

    TECHNICAL_ANALYSIS = "TECHNICAL_ANALYSIS"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    TRADING_STRATEGY = "TRADING_STRATEGY"
    CRYPTO_TERMINOLOGY = "CRYPTO_TERMINOLOGY"
    MARKET_MICROSTRUCTURE = "MARKET_MICROSTRUCTURE"
    TRADING_BASICS = "TRADING_BASICS"
    TRADASTA_DOCUMENTATION = "TRADASTA_DOCUMENTATION"


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """A source document that can be ingested into the knowledge base."""

    title: str
    content: str
    source: str
    category: KnowledgeCategory | str = KnowledgeCategory.TECHNICAL_ANALYSIS
    source_type: KnowledgeSourceType | str = KnowledgeSourceType.MARKDOWN
    tags: list[str] = field(default_factory=list)
    version: str = "1.0"
    id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "source", self.source.strip())
        object.__setattr__(self, "content", self.content.strip())
        object.__setattr__(self, "tags", list(self.tags))
        if not self.title:
            raise ValueError("title is required")
        if not self.content:
            raise ValueError("content is required")
        if not self.source:
            raise ValueError("source is required")
        if self.id is None:
            key = f"{self.title}:{self.source}:{self.content}"
            object.__setattr__(self, "id", sha256(key.encode("utf-8")).hexdigest()[:16])
        if self.updated_at is None:
            object.__setattr__(self, "updated_at", self.created_at)

    @property
    def content_hash(self) -> str:
        """Stable hash used to detect duplicate documents."""
        normalized = self.content.strip().lower()
        return sha256(normalized.encode("utf-8")).hexdigest()

    @property
    def category_name(self) -> str:
        """Expose category as a plain string for API serialization."""
        if isinstance(self.category, KnowledgeCategory):
            return self.category.value
        return str(self.category)

    @property
    def source_type_name(self) -> str:
        """Expose source type as a plain string for API serialization."""
        return (
            self.source_type.value
            if isinstance(self.source_type, KnowledgeSourceType)
            else str(self.source_type)
        )


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """A deterministic chunk extracted from a source document."""

    id: str
    document_id: str
    chunk_index: int
    content: str
    character_count: int
    metadata: dict[str, str | int | None] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", self.content.strip())
        object.__setattr__(self, "character_count", len(self.content))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class KnowledgeEmbedding:
    """A persisted embedding vector for a knowledge chunk."""

    id: str
    chunk_id: str
    embedding: list[float]
    metadata: dict[str, str | int | float | None] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """A natural-language retrieval query with filters and limits."""

    query: str
    top_k: int = 5
    category: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    minimum_score: float = 0.0
    max_top_k: int = 10

    def __post_init__(self) -> None:
        object.__setattr__(self, "query", self.query.strip())
        if not self.query:
            raise ValueError("query is required")
        if self.top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if self.top_k > self.max_top_k:
            raise ValueError(f"top_k must not exceed {self.max_top_k}")
        if self.minimum_score < 0:
            raise ValueError("minimum_score must be non-negative")
        object.__setattr__(self, "tags", list(self.tags or []))

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> RetrievalRequest:
        """Coerce a dict payload into a typed retrieval request."""
        tags = values.get("tags")
        if tags is None:
            normalized_tags: list[str] | None = None
        elif isinstance(tags, str):
            normalized_tags = [tags]
        else:
            normalized_tags = [str(item) for item in tags]
        return cls(
            query=str(values.get("query") or "").strip(),
            top_k=int(values.get("top_k", 5)),
            category=str(values["category"]) if values.get("category") is not None else None,
            source=str(values["source"]) if values.get("source") is not None else None,
            tags=normalized_tags,
            minimum_score=float(values.get("minimum_score", 0.0)),
            max_top_k=int(values.get("max_top_k", 10)),
        )


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """One relevant chunk returned by the retrieval layer."""

    chunk_id: str
    content: str
    score: float
    document_id: str
    title: str
    source: str
    section: str | None = None
    metadata: dict[str, str | int | float | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Outcome of a document ingestion operation."""

    document_id: str
    title: str
    chunks_created: int
    embeddings_created: int
    status: str
    content_hash: str | None = None


@dataclass(frozen=True, slots=True)
class RagContext:
    """Structured retrieval context for later LLM or orchestration layers."""

    query: str
    sources: list[str]
    chunks: list[str]
    total_results: int
    context_text: str = ""


__all__ = [
    "IngestionResult",
    "KnowledgeCategory",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "KnowledgeEmbedding",
    "KnowledgeSourceType",
    "RagContext",
    "RetrievalRequest",
    "RetrievalResult",
]
