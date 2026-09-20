# Database Design

## Current state

The backend does not yet require a production relational database. The current implementation uses:
- local markdown files under `app/data/knowledge/` for knowledge content
- an in-memory or file-backed vector store pattern for retrieval
- runtime configuration loaded from environment variables and `.env`

This is appropriate for an early-stage deterministic backend, but it is not sufficient for a production-grade multi-user system.

## Planned persistence needs

As the platform matures, the following data concerns should be separated:

### 1. Market data
- time-series candles and price snapshots
- normalized OHLCV histories by symbol and interval
- provider metadata and source provenance

### 2. Strategy and signal history
- signal decisions and rationale
- strategy configuration snapshots
- evaluation timestamps and model versions

### 3. Knowledge corpus
- source documents and metadata
- chunk records and embedding references
- retrieval statistics and usage metrics

### 4. Operational data
- application logs
- audit events
- config or feature-flag snapshots

## Recommended target architecture

### Relational database
- PostgreSQL is a good default for operational data and signal history
- Use normalized tables for symbols, time-series entries, strategies, and evaluations

### Vector database
- Use pgvector or a managed vector service for semantic query workloads
- Keep metadata indexing aligned with document source and timestamp filters

### Storage strategy
- Keep source documents as immutable versioned records
- Store embeddings separately from raw documents to support re-indexing
- Maintain a sync process for document ingestion and later cleanup

## Data ownership and integrity

- Domain objects should own the logical rules for validation
- Infrastructure code should map to persistence schemas without encoding trading logic
- Signals should carry provenance about the market data, strategy, and risk gates they depended on

## Migration strategy

When the project moves beyond local storage, migrations should be version-controlled and run as part of CI/CD. Each migration must be tested for idempotence and rollback safety.
