# API Contracts

## Authentication

- `POST /api/v1/auth/register`: first-user bootstrap; creates the initial admin.
- `POST /api/v1/auth/login`: returns a bearer JWT.

## Query

`POST /api/v1/query` accepts `question`, optional `document_id`, `limit`, and `reveal_pii`. `reveal_pii` defaults to `false`; setting it to `true` requires an analyst or admin bearer token and creates an audit event.

## LLM settings

- `GET /api/v1/settings/llm`: admin only; returns metadata and whether a key is configured.
- `PUT /api/v1/settings/llm`: admin only; encrypts a supplied API key before storage.

Secrets are never included in responses.
