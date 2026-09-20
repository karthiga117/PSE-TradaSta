# Deployment

## Local development

The project is designed to run as a local FastAPI service with environment-based configuration.

Typical local steps:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Container deployment

The repository includes a Dockerfile for packaging the backend into a container. Production deployment should add:
- non-root runtime user
- environment-specific settings
- health and readiness checks
- log aggregation
- secrets injection

## Production readiness checklist

- Create isolated dev, test, staging, and production environments
- Configure managed secrets and network restrictions
- Add infrastructure-as-code definitions for deployment automation
- Run smoke tests in deployment pipelines before promotion
- Keep rollback steps documented and rehearsed

## Recommended target platform

The implementation plan indicates Azure as a candidate platform. A production-ready deployment should use Azure-native services only where the requirement is explicit, and every service choice must be documented with the relevant security, cost, and operational trade-offs.

## CI/CD expectations

- Run unit tests on every pull request
- Run lint and type checks during build validation
- Build the container artifact and publish it through a registry
- Deploy only after environment-specific checks pass
- Preserve rollback options for failed releases
