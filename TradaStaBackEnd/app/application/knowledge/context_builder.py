"""Build structured retrieval contexts without inventing new knowledge."""

from __future__ import annotations

from app.domain.knowledge.models import RagContext, RetrievalResult


class RagContextBuilder:
    """Organize retrieved chunks into a limited context window for later orchestration."""

    def __init__(self, *, max_context_chunks: int = 5, max_context_characters: int = 2000) -> None:
        self.max_context_chunks = max(1, max_context_chunks)
        self.max_context_characters = max(1, max_context_characters)

    def build(self, query: str, results: list[RetrievalResult]) -> RagContext:
        """Return a compact context object with deterministic ordering and truncation."""
        limited_results = results[: self.max_context_chunks]
        sources = list(dict.fromkeys(result.source for result in limited_results))
        chunks = [result.content for result in limited_results]
        text_parts: list[str] = []
        total_chars = 0
        for result in limited_results:
            block = (
                f"[{result.title} | {result.source}"
                f"{f' | {result.section}' if result.section else ''}]\n{result.content}"
            )
            if total_chars + len(block) > self.max_context_characters:
                break
            text_parts.append(block)
            total_chars += len(block)
        return RagContext(
            query=query,
            sources=sources,
            chunks=chunks,
            total_results=len(results),
            context_text="\n\n".join(text_parts),
        )


__all__ = ["RagContextBuilder"]
