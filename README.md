# Droit.ai

**Droit.ai** is a privacy-first legal intelligence platform built with a FastAPI backend and Next.js frontend.

---

## Features

- **Modular backend** — API, persistence, and core processing have explicit boundaries
- **Production vector store target** — Qdrant is provided through Docker Compose
- **Multi-format backend ingestion** — TXT, PDF, DOCX, CSV, and XLSX extraction
- **FastAPI foundation** — app factory, environment-backed settings, and versioned health API
- **Privacy-aware processing** — deterministic PII aliases are embedded while encrypted originals remain in PostgreSQL
- **Hybrid retrieval** — organization-scoped cosine and BM25 rankings fused with weighted RRF, then cross-encoder reranked
- **Grounded query API** — provider-agnostic answers with citations through Groq, OpenAI, Anthropic, or Ollama
- **Explainable risk baseline** — missing clauses, asymmetric terms, auto-renewal, jurisdiction, and PII density are scored during ingestion

---

## Project Structure

```
droit/
├── backend/                        # FastAPI service (Phase 1, in progress)
│   ├── app/                        # API, core services, config, and models
│   ├── tests/                      # Backend test suite
│   └── requirements.txt            # Backend Python dependencies
├── frontend/                       # Next.js application
├── docker-compose.yml              # PostgreSQL, Qdrant, optional Redis
├── implementation_plan.md          # Phase-wise delivery plan
├── .env.example                    # API key & config template
└── storage/                        # Local uploads (gitignored)
```

---

## Current Backend Flow

```
Document (TXT, PDF, DOCX, CSV, XLSX)
     │
     ▼
[backend loader] → extracted text + metadata
     │
     ▼
[PII anonymizer] → encrypted mappings + anonymized text
     │
     ▼
[chunker] → PostgreSQL chunks + Qdrant vectors
     │
     └── retrieval core: cosine + BM25 → weighted RRF
```

The retrieval pipeline is exposed through the RAG query endpoint and reranks fused candidates with a cross-encoder before answer generation.

---

## Backend Quick Start

### 1. Create the Python environment

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env for local service and provider settings
```

### 3. Start local data services

```bash
docker compose up -d postgres qdrant
```

### 4. Run the API

```bash
.venv/bin/uvicorn backend.app.main:app --reload
```

The liveness endpoint is available at `http://localhost:8000/api/v1/health/live`, and OpenAPI documentation is available at `http://localhost:8000/docs`.

Qdrant and the embedding model are initialized lazily on the first vector operation, so the liveness endpoint remains available even when indexing infrastructure is offline.

### 5. Run tests

```bash
.venv/bin/python -m pytest backend/tests -q
```

### Authentication and security

The first `POST /api/v1/auth/register` call creates the initial organization admin. Use `POST /api/v1/auth/login` to start a session. Browsers receive an httpOnly `droit_session` cookie and never store the token in JavaScript; non-browser clients can use the returned JWT as a bearer token. `GET /api/v1/auth/me` validates the session and `POST /api/v1/auth/logout` clears it. Set `DROIT_AUTH_REQUIRED=true`, a strong `DROIT_JWT_SECRET`, and `DROIT_SESSION_COOKIE_SECURE=true` outside local development.

Queries return anonymized aliases by default. Setting `reveal_pii=true` requires an analyst or admin token and creates an audit record. Admin-only LLM settings are available at `/api/v1/settings/llm`; API keys are encrypted before storage.

Read [SECURITY.md](SECURITY.md), [PLAN.md](PLAN.md), and the applicable [AGENTS.md](AGENTS.md) before changing sensitive workflows.

## Configuration

All settings are controlled via `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DROIT_DATABASE_URL` | Local PostgreSQL | Async SQLAlchemy connection URL |
| `DROIT_QDRANT_URL` | `http://localhost:6333` | Qdrant API URL |
| `DROIT_QDRANT_COLLECTION` | `droit_legal_documents` | Qdrant collection name |
| `DROIT_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | FastEmbed model |
| `DROIT_STORAGE_ROOT` | `./storage` | Local document storage root |
| `DROIT_CHUNK_SIZE` | `800` | Maximum chunk size in characters |
| `DROIT_CHUNK_OVERLAP` | `150` | Adjacent chunk overlap in characters |
| `DROIT_RETRIEVAL_CANDIDATE_LIMIT` | `30` | Candidate count per retrieval source |
| `DROIT_RETRIEVAL_VECTOR_WEIGHT` | `1.0` | Vector ranking weight in RRF |
| `DROIT_RETRIEVAL_BM25_WEIGHT` | `1.0` | BM25 ranking weight in RRF |
| `DROIT_RETRIEVAL_RRF_K` | `60` | RRF rank constant |
| `DROIT_RETRIEVAL_RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Sentence Transformers cross-encoder model |
| `DROIT_RETRIEVAL_RERANKER_CANDIDATE_LIMIT` | `12` | Fused candidates scored by the reranker |
| `DROIT_ENVIRONMENT` | `development` | Runtime environment name |
| `DROIT_DEBUG` | `false` | FastAPI debug mode |
| `DROIT_AUTH_REQUIRED` | `false` | Reject unauthenticated API requests |
| `DROIT_JWT_SECRET` | Development placeholder | HS256 signing secret for session tokens |
| `DROIT_SESSION_COOKIE_NAME` | `droit_session` | Browser session cookie name |
| `DROIT_SESSION_COOKIE_SECURE` | `false` | Send the session cookie over HTTPS only |
| `DROIT_SESSION_COOKIE_SAMESITE` | `lax` | Session cookie SameSite policy |

---

## Phase 1 Status

- [x] FastAPI app factory, settings, and liveness endpoint
- [x] Backend TXT, PDF, DOCX, CSV, and XLSX loader
- [x] PostgreSQL models for organizations, users, documents, chunks, PII mappings, and jobs
- [x] Alembic initial migration and schema drift checks
- [x] Multipart upload, pasted-text ingestion, idempotency, and job status API
- [x] Transactional document deletion across PostgreSQL, Qdrant, and local storage
- [x] Metadata extraction, deterministic PII anonymization, chunking, and Qdrant indexing
- [x] BM25 and cosine hybrid retrieval with weighted reciprocal rank fusion
- [x] Query API, cross-encoder reranking, and provider-agnostic generation
- [x] Deterministic clause-heuristic risk scoring and persisted breakdowns
- [x] Optional LLM-enriched structured risk scoring with heuristic fallback

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic Settings |
| Relational database | PostgreSQL, SQLAlchemy, Alembic |
| Vector store | Qdrant |
| Frontend | Next.js, React, Tailwind CSS |
| Agents and tools | Pydantic AI, FastMCP |
