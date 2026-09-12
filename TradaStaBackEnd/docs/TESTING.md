# Testing

## Test strategy

The project uses pytest as the primary automated validation suite. The existing tests cover the main deterministic behaviors, including configuration, exceptions, health checks, knowledge retrieval, technical analysis, risk management, and signal generation.

## Current test scopes

- configuration and bootstrap checks
- exception and error handling
- health endpoint validation
- technical-analysis correctness
- risk-evaluation guardrails
- signal-engine behavior under valid and invalid conditions
- local knowledge and retrieval behavior

## Command

```bash
pytest
```

## Recommended additional validation

- linting with Ruff
- static type checking with MyPy
- integration tests against provider mocks
- failure-mode tests for provider outages
- load tests for rate-limiting and latency constraints
- security validation for secrets and request handling

## Release gate

The release process should require all automated tests, linting, and relevant integration checks to pass before deployment. This reduces the risk of shipping logic that is correct in isolation but unsafe in a real environment.
