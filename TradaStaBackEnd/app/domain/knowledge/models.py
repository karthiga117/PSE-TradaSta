"""Knowledge-domain models for semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RetrievalDocument:
    """A single document in the local semantic knowledge corpus."""

    id: str
    title: str
    category: str
    summary: str
    content: str
    source: str = "local_corpus"
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RetrievalMatch:
    """A relevance-ranked source document returned by a retrieval request."""

    id: str
    title: str
    category: str
    summary: str
    content: str
    score: float
    source: str = "local_corpus"
    tags: tuple[str, ...] = field(default_factory=tuple)
