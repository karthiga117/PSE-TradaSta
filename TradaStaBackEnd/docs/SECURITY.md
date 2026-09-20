# Security

## Security posture

The backend currently follows a conservative security model for a prototype and early production foundation. The project focuses on deterministic validation, explicit risk gates, and clean configuration boundaries rather than over-broad trust in external services.

## Key principles
- Validate every incoming request at the API boundary
- Enforce risk rules before publishing any trade signal
- Keep secrets in environment variables or managed secret stores
- Treat market-data and AI providers as untrusted external systems
- Prevent accidental leakage of internal reasoning or private environment data

## Current safeguards

### Input validation
- FastAPI request validation catches malformed data before service logic runs
- Domain models validate required fields and reject invalid payloads
- The risk-management layer checks exposure, portfolio concentration, drawdown, and loss constraints

### Risk controls
- Trade proposals must satisfy stop-loss and take-profit requirements when enabled
- The signal engine blocks unsafe or insufficiently validated decisions
- The system intentionally requires deterministic risk constraints to be met before BUY or SELL output is returned

### Secret handling
- Use `.env` files only for local development
- Do not store production secrets in source control
- Production deployments should use a managed secret store such as Azure Key Vault

## Planned hardening

- Add rate limiting and request throttling at the gateway layer
- Enforce authentication and authorization for privileged endpoints
- Secure all outbound provider calls with TLS and allow-list configuration
- Add dependency scanning and vulnerability monitoring to CI/CD
- Log security-relevant events without exposing confidential credentials
- Review and restrict error-message disclosure to avoid information leakage

## Threat model summary

The most meaningful risks for this backend are:
- malformed or abusive API requests
- unsafe or unbounded trade calculations
- exposure to untrusted provider data
- accidental secret leakage
- noisy or insufficient logs that impair incident response

These risks are reduced through validation, deterministic guardrails, and explicit operational controls.
