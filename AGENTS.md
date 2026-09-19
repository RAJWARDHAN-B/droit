# Droit Agent Guide

## Scope
These rules apply to the whole repository. More specific `AGENTS.md` files refine them for backend and frontend work.

## Engineering rules
- Keep backend application code under `backend/app/` and frontend code under `frontend/src/`.
- Preserve organization scoping on every document, query, setting, and audit operation.
- Never expose original PII by default. PII restoration must be explicit, role-checked, and audited.
- Never log secrets, API keys, passwords, encryption keys, or original PII.
- Use Alembic migrations for schema changes; do not edit production tables manually.
- Prefer focused changes and existing abstractions over new framework layers.
- Do not add Redis, workers, agents, or MCP tools without a concrete current consumer or measured need.

## Validation
- Backend: `.venv/bin/python -m pytest backend/tests -q`
- Frontend: `cd frontend && npm run lint && npm run build`
- For schema changes, run the Alembic upgrade against the local database.

## Documentation
Keep `PLAN.md` current for the active milestone. Put durable architecture decisions in `docs/decisions/`.
