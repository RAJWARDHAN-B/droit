# Architecture

Droit has a FastAPI backend and a Next.js frontend. The backend flow is:

`upload -> extract -> anonymize -> chunk -> embed -> retrieve -> generate`

PostgreSQL stores organizations, users, documents, chunks, encrypted PII mappings, processing jobs, LLM settings, and audit logs. Qdrant stores vectors. Local disk stores source and derived document files.

The default response contains aliases. Original values can only be restored by an authenticated analyst or admin through an explicit request, and the action is audited.

Redis, worker queues, streaming, agents, and MCP are deferred infrastructure rather than required request-path dependencies.
