# Backend Agent Guide

- Use async FastAPI endpoints and SQLAlchemy sessions.
- Keep HTTP concerns in `api/`, business workflows in `services/`, and reusable domain logic in `core/`.
- Add request and response models under `schemas/`.
- Every new table requires an Alembic migration and focused tests.
- Use `current_user` and role dependencies for protected operations.
- Query and document access must remain organization-scoped.
- Persist audit events for authentication-sensitive actions, settings changes, and PII reveals.
- Keep provider secrets in `SecretStr` or encrypted database columns. Never return secret values from APIs.
