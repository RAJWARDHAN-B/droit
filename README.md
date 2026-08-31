# Droit.ai

**Droit.ai** is a privacy-first legal intelligence platform built with a FastAPI backend and Next.js frontend.

---

## Features

- **Modular backend** — API, persistence, and core processing have explicit boundaries
- **Production vector store target** — Qdrant is provided through Docker Compose
- **Multi-format backend ingestion** — TXT, PDF, DOCX, CSV, and XLSX extraction
- **FastAPI foundation** — app factory, environment-backed settings, and versioned health API
- **Privacy-aware persistence** — original PII values are represented by encrypted-only mapping columns

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
[backend loader] → extracted text
     │
     └── next: PII anonymization → chunking → Qdrant indexing
```

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

### 5. Run tests

```bash
.venv/bin/python -m pytest backend/tests -q
```

## Configuration

All settings are controlled via `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DROIT_DATABASE_URL` | Local PostgreSQL | Async SQLAlchemy connection URL |
| `DROIT_QDRANT_URL` | `http://localhost:6333` | Qdrant API URL |
| `DROIT_STORAGE_ROOT` | `./storage` | Local document storage root |
| `DROIT_ENVIRONMENT` | `development` | Runtime environment name |
| `DROIT_DEBUG` | `false` | FastAPI debug mode |

---

## Phase 1 Status

- [x] FastAPI app factory, settings, and liveness endpoint
- [x] Backend TXT, PDF, DOCX, CSV, and XLSX loader
- [x] PostgreSQL models for organizations, users, documents, chunks, PII mappings, and jobs
- [ ] Alembic initial migration
- [ ] Upload processing jobs and status API
- [ ] PII anonymization and Qdrant indexing

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Pydantic Settings |
| Relational database | PostgreSQL, SQLAlchemy, Alembic |
| Vector store | Qdrant |
| Frontend | Next.js, React, Tailwind CSS |
| Agents and tools | Pydantic AI, FastMCP |
