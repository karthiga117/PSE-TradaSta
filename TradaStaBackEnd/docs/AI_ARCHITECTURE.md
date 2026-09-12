# AI Architecture

## High-level intent

The backend is designed to be AI-ready, but not AI-dependent. The core platform is grounded in deterministic logic for technical analysis, risk validation, and signal generation before any generative or external AI services are introduced.

## Current model

The application currently implements:
- deterministic market-data normalization
- objective technical indicators
- strict risk gates
- explainable BUY/SELL/HOLD output generation
- local knowledge retrieval and context preparation

These behaviors do not require a hosted LLM to be correct or reproducible.

## Planned AI integration

Future AI work should follow a layered pattern:
1. Use deterministic services for core trade evaluation
2. Retrieve relevant context from the knowledge system
3. Pass bounded context to a model provider or orchestration layer
4. Require policy checks before any AI-generated recommendation is acted on

## Guardrails

- AI outputs should never bypass the risk-management engine
- Prompt or response data should be versioned and logged for review
- External models should be treated as advisory systems, not approval systems
- Final trade decisions must remain explainable and auditable

## Architecture principle

The AI layer is an add-on service that augments the deterministic platform. It should not replace the domain rules that govern safety, risk, and signal legitimacy.
