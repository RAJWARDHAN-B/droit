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
- The full backend suite passes: 43 tests.
- Frontend lint and production build pass; route shells exist for login, dashboard, upload, documents, settings, and drafting.
- App routes now require a browser JWT token and provide logout.
- The admin settings route can load, save, and test provider configuration without displaying stored keys.
- The document detail route loads its document library and highlights citation excerpts in the anonymized viewer.
- Dedicated authentication, settings, and audit coverage is present.
- JWT 401 responses now clear the browser session and redirect app routes to login.
- Readiness reports PostgreSQL and Qdrant dependency status, and unexpected errors include a request ID.

### Next checks

- Add dedicated auth, settings, and audit assertions beyond the current workflow coverage.
- Replace browser-only JWT storage with a server-side or httpOnly-cookie session before production deployment.
- Begin product work only after deciding whether the deferred agent/MCP scope has a concrete consumer.
- Set `DROIT_AUTH_REQUIRED=true` and a real `DROIT_JWT_SECRET` outside development.
- Add dependency diagnostics to readiness and structured error reporting.

### Deferred

Pydantic AI orchestration, FastMCP, Redis, Celery, SSE, comparison, annotations, drafting, and marketing content remain deferred until a concrete consumer or measured bottleneck justifies them.
