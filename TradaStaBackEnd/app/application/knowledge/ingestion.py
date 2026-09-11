"""Knowledge-base ingestion service for local markdown/text document sources."""

from __future__ import annotations

from pathlib import Path

from app.application.knowledge.embedding import EmbeddingProvider
from app.application.knowledge.vector_store import VectorStore
from app.domain.knowledge.models import (
    IngestionResult,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeEmbedding,
    KnowledgeSourceType,
)


class KnowledgeIngestionService:
    """Split documents into chunks, generate embeddings, and persist them."""

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        *,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.chunk_size = max(1, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def ingest_document(self, document: KnowledgeDocument) -> IngestionResult:
        """Validate, chunk, embed, and persist a single document."""
        if not document.content.strip():
            raise ValueError("Document content cannot be empty.")

        document_hash = document.content_hash
        if self.vector_store.has_document_hash(document_hash):
            return IngestionResult(
                document_id=document.id or document.title,
                title=document.title,
                chunks_created=0,
                embeddings_created=0,
                status="COMPLETED",
                content_hash=document_hash,
            )

        chunks = self.chunk_document(document)
        embeddings_created = 0
        for chunk in chunks:
            embedding_values = self.embedding_provider.embed_text(chunk.content)
            embedding = KnowledgeEmbedding(
                id=f"{chunk.id}-embedding",
                chunk_id=chunk.id,
                embedding=embedding_values,
                metadata={
                    "document_id": chunk.document_id,
                    "category": chunk.metadata.get("category"),
                    "source": chunk.metadata.get("source"),
                    "section": chunk.metadata.get("section"),
                    "tags": chunk.metadata.get("tags", []),
                },
            )
            self.vector_store.add(chunk, embedding)
            embeddings_created += 1

        self.vector_store.register_document_hash(document_hash)
        return IngestionResult(
            document_id=document.id or document.title,
            title=document.title,
            chunks_created=len(chunks),
            embeddings_created=embeddings_created,
            status="COMPLETED",
            content_hash=document_hash,
        )

    def ingest_file(self, path: str | Path) -> IngestionResult:
        """Ingest a supported local knowledge file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Knowledge source not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in {".md", ".txt"}:
            raise ValueError(f"Unsupported knowledge source type: {suffix}")

        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        content = file_path.read_text(encoding="utf-8")
        document = KnowledgeDocument(
            title=title,
            content=content,
            source=str(file_path.name),
            category="TECHNICAL_ANALYSIS",
            source_type=(
                KnowledgeSourceType.MARKDOWN
                if suffix == ".md"
                else KnowledgeSourceType.TEXT
            ),
            tags=["local", "source"],
        )
        return self.ingest_document(document)

    def ingest_directory(self, path: str | Path) -> list[IngestionResult]:
        """Ingest all supported documents from a directory."""
        directory = Path(path)
        if not directory.exists():
            raise FileNotFoundError(f"Knowledge directory not found: {directory}")

        results: list[IngestionResult] = []
        for file_path in sorted(directory.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in {".md", ".txt"}:
                results.append(self.ingest_file(file_path))
        return results

    def chunk_document(self, document: KnowledgeDocument) -> list[KnowledgeChunk]:
        """Split a document into deterministic chunks while preserving sections."""
        content = document.content.strip()
        if not content:
            return []

        sections = [section.strip() for section in content.split("\n\n") if section.strip()]
        chunks: list[KnowledgeChunk] = []
        buffer: list[str] = []
        buffer_length = 0
        section_name: str | None = None

        for section in sections:
            line = section.strip()
            if line.startswith("#"):
                section_name = line.lstrip("#").strip() or section_name
            if not line:
                continue

            if buffer and buffer_length + len(line) > self.chunk_size:
                chunk_text = "\n\n".join(buffer)
                chunks.append(
                    self._build_chunk(document, chunk_text, len(chunks), section_name=section_name)
                )
                if self.chunk_overlap > 0:
                    overlap_chars = max(1, self.chunk_overlap)
                    trimmed = " ".join(buffer)
                    if len(trimmed) > overlap_chars:
                        buffer = [trimmed[-overlap_chars:]]
                    else:
                        buffer = [trimmed]
                    buffer_length = len(buffer[0])
                else:
                    buffer = []
                    buffer_length = 0

            buffer.append(line)
            buffer_length += len(line)

        if buffer:
            chunk_text = "\n\n".join(buffer)
            chunks.append(
                self._build_chunk(document, chunk_text, len(chunks), section_name=section_name)
            )

        return [chunk for chunk in chunks if chunk.content]

    def _build_chunk(
        self,
        document: KnowledgeDocument,
        content: str,
        index: int,
        *,
        section_name: str | None,
    ) -> KnowledgeChunk:
        chunk_id = f"{document.id}:{index}"
        metadata: dict[str, str | int | list[str] | None] = {
            "title": document.title,
            "source": document.source,
            "section": section_name,
            "category": document.category_name,
            "tags": list(document.tags),
        }
        return KnowledgeChunk(
            id=chunk_id,
            document_id=document.id or document.title,
            chunk_index=index,
            content=content,
            character_count=len(content),
            metadata=metadata,
        )


__all__ = ["KnowledgeIngestionService"]
