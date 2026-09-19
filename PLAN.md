# Active Plan

## Milestone: Secure and stabilize the core workflow

### Goals

- Make response de-anonymization explicit, authorized, and audited.
- Persist admin-managed LLM settings with encrypted credentials.
- Add authentication and basic roles.
- Verify the complete upload, processing, query, and deletion workflow.
- Establish a clean frontend route structure.
- Improve operational errors and health visibility before distributed infrastructure.

### Current implementation

- JWT bootstrap registration and login endpoints exist.
- Admin and analyst role dependencies exist.
- Query responses default to anonymized aliases.
- `reveal_pii` requires an analyst or admin and creates an audit event.
- LLM settings are persisted per organization with encrypted API keys.
- Alembic migration `6c5e9f4f3b2` adds settings and audit tables.

### Next checks

- Start PostgreSQL and run the focused API tests.
- Add dedicated auth, settings, and audit tests.
- Add route-level frontend tests and wire login state.
- Set `DROIT_AUTH_REQUIRED=true` and a real `DROIT_JWT_SECRET` outside development.

### Deferred

Pydantic AI orchestration, FastMCP, Redis, Celery, SSE, comparison, annotations, drafting, and marketing content remain deferred until a concrete consumer or measured bottleneck justifies them.
