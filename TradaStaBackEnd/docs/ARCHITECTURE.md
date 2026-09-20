# Architecture

## Overview

TradaSta AI is built as a layered, deterministic backend for market intelligence and signal generation. The system separates domain logic, application services, infrastructure adapters, and HTTP endpoints so that trading rules remain explainable and testable.

## Layered design

### 1. Presentation layer
- FastAPI application bootstrap in `app/main.py`
- Versioned API router at `app/api/v1/router.py`
- Endpoint modules for health, market data, analysis, risk, signals, and knowledge

### 2. Application services
- `app/application/technical_analysis/service.py` calculates normalized OHLCV metrics and indicator outputs
- `app/application/risk_management/service.py` validates trade proposals and portfolio constraints
- `app/application/signal_engine.py` combines price, technical, and risk inputs into BUY/SELL/HOLD output
- `app/application/knowledge/*` handles chunking, embedding, retrieval, and context assembly

### 3. Domain layer
- Entities and models express trade-specific concepts without framework coupling
- Core domain objects include market data, technical signals, risk assessments, knowledge documents, and retrieval results
- Deterministic rules should remain in this layer wherever practical

### 4. Infrastructure layer
- Adapters decouple external providers from the application
- Current provider implementation integrates CoinGecko market-data APIs
- Knowledge documents are stored as local markdown files and processed into a vector index in memory or on disk

## Runtime flow

1. The FastAPI app loads environment settings and logging.
2. API requests validate and normalize input through Pydantic models.
3. Services orchestrate domain logic and provider calls.
4. Risk and signal decisions are generated in a deterministic manner before they are returned.
5. Knowledge retrieval uses chunking, metadata filtering, and bounded context assembly for downstream AI orchestration.

## Design principles
- Determinism before optimization
- Clear separation between domain logic and infrastructure
- Reject unsafe or invalid trade proposals before execution
- Prefer explainable outputs over opaque black-box behavior
- Keep external integrations behind adapters

## Extension points
- Add new market-data providers by implementing the provider interface
- Extend technical-analysis strategies without altering endpoint contracts
- Swap or add vector store backends later without changing domain logic
- Layer future LLM orchestration behind a clear service boundary

## Current state

The backend currently focuses on deterministic capabilities, including:
- market-data access
- technical indicator computation
- portfolio and risk validation
- trading-signal generation
- local knowledge retrieval and context creation

Production-grade services such as persistent databases, caching, authentication, and hosted AI inference are represented as planned future additions rather than hard dependencies of the current backend.
