# API Design

## Goals

The API exposes a small, versioned surface for portfolio intelligence and trading signals. The design emphasizes stable contracts, deterministic outputs, and explicit validation for risk-sensitive workflows.

## Versioning

The project uses `/api/v1` as the versioned prefix.

## Core endpoints

### Health
- `GET /` — service root status
- `GET /api/v1/health` — health check for monitoring and deployment probes

### Market data
- `GET /api/v1/market-data/{symbol}/price` — current market price
- `GET /api/v1/market-data/{symbol}/ohlcv` — normalized candle data for a chosen timeframe

### Analysis
- `GET /api/v1/analysis/{symbol}` — technical-analysis summary for a symbol

### Risk
- `POST /api/v1/risk/evaluate` — evaluate whether a trade request satisfies risk gates

### Signals
- `POST /api/v1/signals` — generate a BUY/SELL/HOLD decision using market, analysis, and risk inputs

### Knowledge
- `POST /api/v1/knowledge/search` — query the local knowledge corpus
- `POST /api/v1/knowledge/ingest` — ingest markdown content into the local knowledge store
- `GET /api/v1/knowledge/context` — assemble retrieval context for downstream AI tasks

## Request and response conventions

### Success responses
- HTTP 200 for read operations and deterministic evaluations
- HTTP 201 for successful ingestion when the endpoint creates a new record

### Error responses
- Validation errors return 422 for malformed requests
- Domain or service-level errors should return structured error payloads with machine-readable reasons

### Payload style
- Request bodies are JSON objects with explicit fields
- Decimal-like monetary and percentage values are accepted as strings or numeric values where appropriate
- Response payloads favor clear names such as `signal`, `confidence`, `reasoning`, and `risk_assessment`

## Validation rules

- Symbols must be valid and normalized before provider queries
- Timeframes must be supported by the provider and technical-analysis layer
- Risk requests must satisfy portfolio and drawdown constraints
- BUY/SELL signal generation requires risk validation before returning a publishable result

## Resilience considerations

- Provider failures should return controlled errors rather than uncaught exceptions
- Timeouts and retries should be applied at the infrastructure boundary
- The system should never silently degrade into unsafe trade decisions

## Future API evolution

Upcoming API work should preserve backward compatibility by versioning more significant changes under `/api/v2` or complementary capability-specific routes instead of modifying current contracts in place.
