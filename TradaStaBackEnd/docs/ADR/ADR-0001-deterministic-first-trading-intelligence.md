# ADR-0001: Deterministic-first trading intelligence architecture

- Status: Accepted

## Context

The backend needs to generate trading insights from market data, technical indicators, and risk controls while staying predictable and auditable. A purely opaque AI-first design would be difficult to verify and would risk unsafe recommendations without a deterministic safety layer.

## Decision

Adopt a deterministic core that evaluates market conditions, calculates technical indicators, enforces risk gates, and produces explainable BUY/SELL/HOLD signals before any external AI services are introduced.

## Consequences

### Positive
- Rules are transparent and explainable
- Hidden bugs are easier to test and reason about
- Risk controls remain enforceable even without an LLM
- Knowledge retrieval can be layered in cleanly for future AI augmentation

### Negative
- The system may be less flexible than a purely model-driven design
- Some advanced reasoning capabilities require additional integration work
- Deterministic rules must be maintained alongside AI features as the product evolves

## Alternatives considered

### AI-first signal generation
This approach would be faster to prototype but would make safety checks harder to enforce and reason about.

### Fully externalized decision logic
This would make the backend more dependent on remote providers and lessen local auditability.

## Result

The project is intentionally structured so that deterministic logic remains the source of truth, while AI and external services act as optional enhancement layers.
