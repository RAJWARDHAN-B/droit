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

## LLM settings

- `GET /api/v1/settings/llm`: admin only; returns metadata and whether a key is configured.
- `PUT /api/v1/settings/llm`: admin only; encrypts a supplied API key before storage.

Secrets are never included in responses.
