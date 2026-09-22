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
- The full backend suite passes: 45 tests.
- Frontend lint and production build pass; route shells exist for login, dashboard, upload, documents, settings, and drafting.
- App routes now require a browser JWT token and provide logout.
- The admin settings route can load, save, and test provider configuration without displaying stored keys.
- The document detail route loads its document library and highlights citation excerpts in the anonymized viewer.
- Dedicated authentication, settings, and audit coverage is present.
- JWT 401 responses now clear the browser session and redirect app routes to login.
- Browser sessions use an httpOnly `droit_session` cookie; `/auth/me` validates it and `/auth/logout` clears it.
- Legal and layman summaries are available per document and cached by style.
- Conversation history is persisted with anonymized messages and citations.
- Risk assessment now covers ten clause categories with configurable weights, severity, source spans, and enrichment status.
- Readiness reports PostgreSQL and Qdrant dependency status, and unexpected errors include a request ID.

### Next checks

- Begin product work only after deciding whether the deferred agent/MCP scope has a concrete consumer.
- Set `DROIT_AUTH_REQUIRED=true`, a real `DROIT_JWT_SECRET`, and `DROIT_SESSION_COOKIE_SECURE=true` outside development.

### Known gaps

- Drafting is a UI shell only; the functional module is specified as Phase 5 in `implementation_plan.md`.

### Deferred

Pydantic AI orchestration, FastMCP, Redis, Celery, SSE, comparison, annotations, drafting, and marketing content remain deferred until a concrete consumer or measured bottleneck justifies them.
