# Observability

## Purpose

Observability allows the system to be operated safely, debugged quickly, and monitored in production. The backend should expose enough telemetry to answer: what happened, why it happened, and whether the service is healthy.

## Current logging

The app configures structured logging at startup and uses FastAPI exception handlers. This is the foundation for environment-aware logging.

## Recommended telemetry
- application logs for requests and errors
- health-check endpoints for uptime verification
- request duration and latency metrics
- provider failure counts
- vector retrieval statistics and context size metrics
- risk-validation pass/fail counters

## Patterns to add

### Standard metrics
- request rate
- error rate
- p95 latency
- external provider latency
- signal generation count by direction

### Alerts
- elevated error rate
- provider outage or degradation
- repeated risk rejections or abnormal signal patterns
- unscheduled downtime or repeated startup failures

## Operational guidance

- Keep logs structured and searchable
- Mask secrets and sensitive personal or account data
- Correlate logs with request IDs where possible
- Retain metrics and logs according to a documented retention policy

## Production expectation

The backend should surface enough telemetry for both automated monitoring and human incident response. A production environment without observability is not considered ready for release.
