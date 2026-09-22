# API Contracts

## Authentication

- `POST /api/v1/auth/register`: first-user bootstrap; creates the initial admin.
- `POST /api/v1/auth/login`: sets an httpOnly `droit_session` cookie and returns the same JWT for non-browser clients.
- `GET /api/v1/auth/me`: returns the authenticated user; browsers use it to validate the session cookie.
- `POST /api/v1/auth/logout`: clears the session cookie.

Requests authenticate with either the session cookie or an `Authorization: Bearer` header. Browser clients must send credentials with every request and never store the token in JavaScript-readable storage.

Cookie behavior is controlled by `DROIT_SESSION_COOKIE_NAME`, `DROIT_SESSION_COOKIE_SECURE`, and `DROIT_SESSION_COOKIE_SAMESITE`.

## Query

`POST /api/v1/query` accepts `question`, optional `document_id`, `limit`, and `reveal_pii`. `reveal_pii` defaults to `false`; setting it to `true` requires an analyst or admin bearer token and creates an audit event.

## Summaries

- `POST /api/v1/documents/{id}/summary`: accepts `style` (`legal` or `layman`) and optional `refresh`; returns an anonymized cached summary.

Legal summaries preserve defined terms and clause references. Layman summaries explain obligations in plain English. Original PII is never sent to the provider or stored in the summary.

## Conversations

- `POST /api/v1/conversations`: create a user-scoped conversation, optionally scoped to a document.
- `GET /api/v1/conversations` and `GET /api/v1/conversations/{id}`: list or reopen saved history.
- `POST /api/v1/conversations/{id}/messages`: answer and persist a question plus its citations.
- `PATCH /api/v1/conversations/{id}`: rename a conversation.
- `DELETE /api/v1/conversations/{id}`: delete saved history.

Messages are persisted with anonymized aliases only. Revealed PII is never written to conversation history.

## Risk assessment

Document ingestion stores a 0-100 explainable risk score. The baseline checks indemnification, liability, confidentiality, data protection, governing law, termination, payment, disputes, IP ownership, assignment, asymmetric wording, auto-renewal, and PII density. Findings include severity, category score, and source spans where the finding comes from document text. Weights are configurable through `DROIT_RISK_WEIGHT_*` settings. Optional LLM enrichment is bounded and records `llm_status` as `applied` or `failed`.

## LLM settings

- `GET /api/v1/settings/llm`: admin only; returns metadata and whether a key is configured.
- `PUT /api/v1/settings/llm`: admin only; encrypts a supplied API key before storage.

Secrets are never included in responses.
