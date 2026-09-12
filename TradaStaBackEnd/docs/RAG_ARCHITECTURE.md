# RAG Architecture

## Purpose

The knowledge layer provides a retrieval-augmented generation foundation without requiring an external LLM at runtime. The design allows the system to search local trading knowledge, assemble a bounded context, and later pass that context to downstream AI orchestration.

## Components

### Knowledge source
- Markdown text files stored under `app/data/knowledge/`
- Each document includes structured or domain-specific trading content

### Ingestion pipeline
1. Read a source document
2. Normalize the content
3. Chunk content into bounded segments
4. Attach metadata such as topic, source, and timestamp
5. Store the chunks and metadata in the retrieval layer

### Retrieval pipeline
- Query text is transformed and compared with stored chunk embeddings or text metadata
- Results are filtered by topic, source, or score thresholds
- Matching chunks are ranked and limited to a bounded top-k set

### Context assembly
- The top matching chunks are stitched into a compact context window
- Context size is intentionally constrained to keep follow-up model calls predictable and cost-aware

## Operational goals
- Deterministic retrieval outcomes for local documents
- Transparent, explainable context generation
- Low-latency local search for non-LLM-assisted workflows
- Extensibility for future AI orchestration

## Constraints
- The current stack favors deterministic local retrieval before hosted AI services are introduced
- Vector search is treated as an implementation detail behind a service interface
- The retrieval layer must never bypass risk or domain rules when generating trade advice
