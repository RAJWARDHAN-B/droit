# Droit — Full Production App: Phase-Wise Implementation Plan

## Overview

Droit is being evolved from a CLI-based legal RAG pipeline into a **full-stack, production-grade Legal Intelligence Platform**. The existing Python pipeline (ingestion → chunking → embedding → retrieval → generation) becomes the backbone of a multi-agent backend, exposed via FastAPI + FastMCP, and consumed by a sleek Next.js frontend.

## Current Status (2026-09-17)

### Active milestone (2026-09-19)

The active priority is to secure and stabilize the existing workflow before adding distributed infrastructure or additional product modules. Authentication, role checks, audited PII reveal, persisted encrypted LLM settings, focused end-to-end tests, route separation, and operational error handling are the current release gate.

### Done

- Phase 1 backend foundation, ingestion, encrypted PII mappings, anonymized indexing, hybrid retrieval, cited answers, job status, deletion rollback, and heuristic risk scoring are implemented and tested.
- Optional structured LLM risk enrichment with heuristic fallback is implemented.
- The current frontend supports pasted text, multi-file upload queues, processing-stage polling, document search and risk filters, deletion, anonymized document viewing, scoped queries, citations, and risk findings.

### Remaining

- Add dedicated authentication, settings, and audit assertions beyond the current workflow coverage.
- Replace browser-only JWT storage with a server-side or httpOnly-cookie session before production deployment.
- Begin product work only after deciding whether the deferred agent/MCP scope has a concrete consumer.
- Add dependency diagnostics to readiness and structured error reporting.
- Defer agents, MCP, Redis, workers, streaming, and content modules until a concrete consumer or measured bottleneck justifies them.

---

## Confirmed Decisions

| Decision | Choice |
|---|---|
| Tenancy | **Single-org** for now; multi-tenancy as future scope |
| Risk score | Clause-heuristic + LLM (missing clauses, asymmetric obligations, PII density) |
| Blog content | **MDX files** (git-versioned, no CMS) |
| Document storage | **Local disk** only; no S3/cloud |

---

## Tech Stack (Revised & Recommended)

### Frontend
| Tool | Version | Why |
|---|---|---|
| **Next.js** | 16.x (App Router) | Current project version, RSC, streaming, great DX |
| **TypeScript** | 5.x | Type safety across the board |
| **Tailwind CSS** | 4.x | Current project version, natural fit for Next.js |
| **shadcn/ui** | latest | Accessible, unstyled-by-default components on Radix UI |
| **Zustand** | 5.x | Lightweight client state (auth, settings) |
| **TanStack Query** | 5.x | Server state, caching, invalidation |
| **Framer Motion** | 13.x | Smooth animations and micro-interactions |
| **NextAuth.js** | v5 beta | Current project version; free, self-hosted credentials + JWT |

> [!NOTE]
> **Why NextAuth over Clerk?** Clerk is great but has a paid tier. NextAuth v5 is free, runs locally, and is more than enough for single-org. We can migrate to Clerk if multi-tenancy is needed later.

### Backend
| Tool | Version | Why |
|---|---|---|
| **FastAPI** | 0.115.x | Async, fast, great OpenAPI docs, already Python ecosystem |
| **Pydantic AI** | 0.x (latest) | User requested; clean agent abstraction over multiple LLM providers |
| **FastMCP** | 2.x | User requested; MCP server for tool exposure |
| **SQLAlchemy** | 2.0 | Modern async ORM |
| **Alembic** | 1.x | DB migrations |
| **Microsoft Presidio** | 2.x | Industry-standard PII detection + anonymization |

### Databases
| Tool | Why |
|---|---|
| **PostgreSQL** | Relational data: docs, PII maps, users, audit logs |
| **Qdrant** | Persistent local vector storage with filtering and payload indexing |
| **Redis** | Phase 4+: query caching, session context store. Not needed in Phase 1. |

> [!IMPORTANT]
> **Vector store**: Qdrant is the only supported vector store and runs locally through Docker Compose.

### LLM Providers (provider-agnostic via Pydantic AI)
- **Groq** (default, fast, free tier)
- **OpenAI** (optional)
- **Anthropic** (optional)
- **Ollama** (local, data never leaves machine)

### Document Storage
- **Local disk** with org-namespaced directories
- Abstracted behind a `StorageBackend` interface so cloud is a future drop-in

```
storage/
  uploads/
    org_default/
      <doc_id>_original.<ext>
      <doc_id>_raw_text.txt
      <doc_id>_anonymized_text.txt
```

---

---

## Ollama / Local LLM Scope

The Ollama endpoint is a **global app-level setting** managed by an admin. Provider credentials are encrypted at rest. Per-user endpoint and provider overrides are deferred until role or multi-tenancy requirements justify them.

---

## Backend Module Inventory

The experimental CLI and notebook-export code has been removed. `backend/app/` is the sole Python application package, avoiding duplicate configuration and pipeline implementations.

| Module | Backend location | Status |
|--------|------------------|--------|
| API app and config | `backend/app/main.py`, `backend/app/config.py` | ✅ Implemented |
| Database models | `backend/app/models/` | ✅ Implemented |
| Document loader | `backend/app/core/ingestion/loader.py` | ✅ TXT, PDF, DOCX, CSV, XLSX |
| Metadata extractor | `backend/app/core/ingestion/metadata_extractor.py` | ✅ File hash, size, type, and text statistics |
| PII anonymizer | `backend/app/core/pii/` | ✅ NER + pattern recognizers, deterministic aliases, encrypted mappings |
| Chunker | `backend/app/core/chunking/` | ✅ Implemented |
| Qdrant indexer | `backend/app/core/embedding/` | ✅ Implemented with org/document payloads |
| Hybrid retriever | `backend/app/core/retrieval/` | ✅ BM25 + cosine RRF, query API, and cross-encoder reranking |
| Provider-agnostic generator | `backend/app/core/generation/` | ✅ Groq, OpenAI, Anthropic, and Ollama |
| Risk scorer and enrichment | `backend/app/core/risk/` | ✅ Heuristic baseline, persisted breakdown, optional structured LLM enrichment |

Operational note: Qdrant and FastEmbed dependencies are initialized on first vector use so API liveness does not depend on indexing infrastructure startup.

---

## Proposed Additional Features

Beyond what you listed, here are features worth adding across phases:

1. **Document Comparison Mode** — diff two contracts side-by-side (e.g., compare two NDA versions)
2. **Clause Extraction & Library** — extract all clauses by type (termination, liability, IP) across docs into a searchable clause library
3. **Timeline View** — visual timeline of all dates/obligations extracted from a doc
4. **Audit Trail** — every query, answer, and document action is logged (who asked what, when)
5. **Export Answers** — export chat answers as PDF reports with citations
6. **Annotation Layer** — highlight and annotate clauses in the document viewer
7. **Webhook Notifications** — notify orgs when document processing completes
8. **Role-Based Access** — admin, analyst, viewer roles within an org
9. **Document Expiry Alerts** — alert when a contract is approaching its end date
10. **Multi-language Support** — extract and query non-English legal docs

---

## Phase-Wise Plan

---

## Phase 1 — Foundation & Core Backend API
**Goal**: Migrate CLI pipeline to a production FastAPI backend with full document processing, PII handling, and a working RAG API. No frontend yet.

**Duration estimate**: 2–3 weeks

### Backend (`backend/`)

#### [NEW] `backend/` — Project root for the FastAPI service

```
backend/
├── app/
│   ├── main.py               # FastAPI app factory
│   ├── config.py             # Pydantic Settings
│   ├── database.py           # SQLAlchemy engine + session
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── document.py       # Document, DocumentChunk
│   │   ├── pii_mapping.py    # PIIMapping (alias ↔ original)
│   │   └── organization.py   # Org, User
│   ├── schemas/              # Pydantic request/response schemas
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py
│   │   │   ├── documents.py  # Upload, list, delete endpoints
│   │   │   ├── query.py      # RAG query endpoint
│   │   │   └── settings.py   # LLM provider settings
│   ├── core/                 # Business logic
│   │   ├── ingestion/        # loader.py, metadata_extractor.py (extended)
│   │   ├── pii/              # pii_detector.py, pii_anonymizer.py
│   │   ├── chunking/         # splitter.py
│   │   ├── embedding/        # indexer.py
│   │   ├── retrieval/        # retriever.py (+ BM25 hybrid)
│   │   ├── generation/       # generator.py (provider-agnostic)
│   │   └── risk/             # risk_scorer.py
│   ├── agents/               # Pydantic AI Agents
│   │   ├── orchestrator.py   # Master orchestrator agent
│   │   ├── ingestion_agent.py
│   │   ├── pii_agent.py
│   │   ├── retrieval_agent.py
│   │   └── summarization_agent.py
│   └── mcp/                  # FastMCP tool definitions
│       ├── server.py
│       └── tools/
│           ├── document_tools.py
│           ├── query_tools.py
│           └── summary_tools.py
├── alembic/                  # DB migrations
├── tests/
├── Dockerfile
└── requirements.txt
```

#### Key Phase 1 Tasks:

**1.1 — Project Restructure**
- Keep all Python application code under `backend/app/`; do not recreate a parallel root package
- [x] Set up FastAPI with lifespan events and async database sessions
- [x] Set up PostgreSQL + Alembic migrations

**1.2 — Document Ingestion API** (`POST /api/v1/documents/upload`)
- [x] Accept PDF, DOCX, TXT, CSV, XLSX, and pasted text
- [x] Add Excel/CSV loaders with row and header context
- [x] Store raw file and extracted text on disk and persist the `Document` record
- [x] Create an idempotent processing job and return its document ID and job ID
- [x] Expose `GET /api/v1/jobs/{job_id}` for processing status
- [x] Roll back local files, PostgreSQL records, and Qdrant points when processing fails
- [x] Delete PostgreSQL records, local files, and Qdrant points when a document is deleted

**1.3 — PII Detection & Anonymization** (NEW)
- [x] Use `presidio-analyzer` with deterministic fallback recognizers for PII detection
- [x] Replace repeated PII with stable per-document aliases such as `[PERSON_1]` and `[EMAIL_1]`
- [x] Encrypt original values and store alias mappings in PostgreSQL
- [x] Chunk and embed anonymized text only
- [x] Complete coverage for names, organizations, and locations via spaCy NER, plus emails, phones, SSN, Aadhaar, and financial identifiers via pattern recognizers
- [x] Preserve dates, money, and legal references verbatim so obligation terms stay answerable
- [x] Fail fast when the NER model is missing in production instead of silently degrading to regex-only
- [x] Add response de-anonymization from encrypted mappings
- [x] Add authorized, audited de-anonymization for responses

**1.4 — Hybrid Retrieval (Cosine + BM25)**
- [x] Add `rank_bm25` and organization-scoped lexical candidates
- [x] Query Qdrant with organization and optional document filters
- [x] Implement configurable weighted Reciprocal Rank Fusion (RRF)
- [x] Add cross-encoder reranking
- [x] Expose retrieval through the RAG query endpoint

**1.5 — Provider-Agnostic LLM Generator**
- [x] Refactor `generator.py` to support: Groq, OpenAI, Anthropic, Ollama
- [x] Accept `provider`, `model`, `api_key`, `base_url` (for Ollama) at runtime
- [x] Store the app-level LLM config in DB; only admins can change it

**1.6 — Risk Scorer** (NEW)
- [x] Analyze document for missing clauses, asymmetric obligations, jurisdiction issues, auto-renewal clauses, and PII density
- [x] Return and persist `risk_score` (0–100) and an explainable `risk_breakdown`
- [x] Enrich the heuristic baseline with an optional LLM call and structured Pydantic output

**1.7 — Pydantic AI Agents + FastMCP (deferred)**
- [ ] `IngestionAgent`: Orchestrates upload → extract → PII → chunk → embed → risk score (deferred)
- [ ] `PIIAgent`: Handles PII detection, anonymization, and de-anonymization for responses
- [ ] `RetrievalAgent`: Runs hybrid search + reranking
- [ ] `SummarizationAgent`: Produces legal-jargon or layman summaries
- [ ] `OrchestratorAgent`: Routes user queries to the right agent(s)
- [ ] FastMCP server exposes all agent capabilities as MCP tools (for future integrations; deferred)
- [ ] De-anonymization is an explicit authorized operation; external LLM calls and default responses use aliases, and every reveal is audited

**1.8 — Context Enrichment Store (deferred)**
- [ ] `POST /api/v1/session/page-visit` — store last 5 page visits per session
- [ ] `GET /api/v1/session/context` — returns current enrichment context
- [ ] Query endpoint reads session context and prepends it to the system prompt

---

## Phase 2 — Next.js Frontend (Core UI)
**Goal**: Build the main application UI: document upload, RAG query interface, document library, and document viewer. The initial workflow and route shells are implemented; authentication wiring and focused UI validation remain.

**Duration estimate**: 3–4 weeks

### Frontend (`frontend/`)

```
frontend/
├── app/
│   ├── (app)/                    # Auth-protected app routes
│   │   ├── dashboard/            # Document library
│   │   ├── documents/[id]/       # Document viewer + chat
│   │   ├── upload/               # Upload page
│   │   ├── settings/             # LLM provider settings, API keys
│   │   └── drafting/             # Legal doc drafting (UI shell only, Phase 1)
│   ├── (marketing)/              # Public pages
│   │   ├── page.tsx              # Landing page
│   │   ├── blog/                 # Blog index + MDX posts
│   │   ├── legal-guides/         # NDA, TnC, IP, Employment guides
│   │   └── pricing/
│   └── layout.tsx
├── components/
│   ├── ui/                       # shadcn/ui base components
│   ├── upload/
│   │   ├── DropZone.tsx          # Drag-and-drop multi-format upload
│   │   ├── PasteModal.tsx        # Paste raw text
│   │   └── UploadProgress.tsx    # Processing progress indicator
│   ├── documents/
│   │   ├── DocumentCard.tsx      # Library card with risk badge
│   │   ├── DocumentViewer.tsx    # PDF/text viewer with annotation
│   │   └── RiskScoreBadge.tsx    # Visual risk indicator
│   ├── chat/
│   │   ├── ChatPanel.tsx         # Main chat interface
│   │   ├── ScopeToggle.tsx       # Global vs. doc-specific toggle
│   │   ├── MessageBubble.tsx     # With citation chips
│   │   └── FloatingChatbot.tsx   # Floating icon + mini-window (info pages)
│   ├── settings/
│   │   └── LLMProviderForm.tsx   # Ollama endpoint / API key config
│   └── drafting/
│       └── DraftingShell.tsx     # Placeholder UI for future module
```

#### Key Phase 2 Tasks:

**2.1 — Design System**
- [x] Dark mode-first, minimalist aesthetic
- [x] Color palette: deep navy/slate base, gold/amber accents (legal brand)
- [ ] Typography: Inter (UI), Playfair Display (headings)
- [x] Glass morphism cards, subtle gradients, smooth transitions

**2.2 — Document Upload UI**
- [x] Drag-and-drop zone supporting: PDF, DOCX, TXT, CSV, XLSX
- [x] "Paste Text" tab — textarea for direct text input
- [x] Processing status polling: Uploading → Extracting → PII Scan → Indexing → Done
- [x] Multi-file upload queue

**2.3 — Document Library (Dashboard)**
- [x] List view of all uploaded documents
- [x] Risk score badge with explainable findings
- [ ] Grid view and filters for document type and date
- [ ] Bulk actions: delete, re-index

**2.4 — Document Viewer + In-context Chat**
- [x] Split workspace: document viewer + chat panel
- [x] Scope control for one document vs. all documents
- [x] Citation entries select the relevant source document
- [ ] Scroll to the cited chunk in the viewer
- [ ] Summary panel: legal summary tab + layman summary tab

**2.5 — Floating Chatbot (Info Pages)**
- [ ] Floating icon (bottom-right) on all marketing/info pages
- [ ] Clicks open a mini chat window (not full page)
- [ ] Scope toggle in mini window
- [ ] Context enrichment: reads current page URL + last 5 visits → informs system prompt

**2.6 — Settings Page**
- [x] LLM Provider selector: Groq / OpenAI / Anthropic / Ollama
- [x] For Ollama: custom base URL field (e.g., `http://localhost:11434`)
- [x] API key input with show/hide toggle
- [x] Test connection button

The protected backend settings API and frontend settings workflow are implemented.

**2.7 — Legal Doc Drafting Shell**
- [ ] Placeholder page for the future Phase 5 module
- [ ] Text area for prompt input (disabled or non-functional)
- [ ] Template picker UI (NDA, MSA, Employment Agreement)
- [ ] "Generate Draft" button (disabled, shows tooltip: "Coming in next release")

---

## Phase 3 — Information Pages & Content Layer
**Goal**: Build public marketing + information pages, blog system, and NDA/TnC guide pages.

**Duration estimate**: 1–2 weeks

**3.1 — Landing Page**
- Hero section with product value proposition + animated demo
- Feature highlights: PII Protection, Risk Scoring, Hybrid RAG, Local LLM support
- CTA: "Upload your first document"

**3.2 — Legal Guide Pages**
- `/legal-guides/nda` — What is an NDA, common clauses, risks
- `/legal-guides/terms-and-conditions` — TnC breakdown
- `/legal-guides/msa` — Master Services Agreement guide
- `/legal-guides/employment-agreement`
- `/legal-guides/ip-assignment`
- Each page has the floating chatbot with page-context enrichment

**3.3 — Blog System (MDX)**
- MDX-based blog in `app/(marketing)/blog/`
- Syntax-highlighted code, rich typography
- Tags, reading time, author cards

**3.4 — Context Enrichment Integration**
- Page visit tracker: on every page load, `POST /api/v1/session/page-visit` with page slug
- FloatingChatbot reads last 5 visits and sets context header
- System prompt appended: "The user has been browsing: [NDA Guide, TnC Guide, ...]. Tailor your response accordingly."

---

## Phase 4 — Advanced Features & Polish
**Goal**: Add power features, evaluation pipeline, performance, and production hardening.

**Duration estimate**: 3–4 weeks

**4.1 — Document Comparison Mode**
- Select 2 documents → generate side-by-side diff of key clauses
- Powered by LLM structured extraction + visual diff rendering

**4.2 — Clause Extraction & Library**
- Extract all clauses by type (termination, IP, liability, confidentiality) across all docs
- Searchable clause library view

**4.3 — Annotation Layer**
- Highlight text in document viewer → add note
- Notes stored per-doc-per-user in DB
- Exportable as PDF report

**4.4 — Timeline View**
- Extract all dates/obligations → visual timeline component

**4.5 — RAG Evaluation Pipeline (RAGAS)**
- Integrate existing RAGAS evaluation code into a backend job
- Expose evaluation scores in an admin dashboard

**4.6 — Audit Trail**
- Every query/answer logged: user, timestamp, query, retrieved_chunks, answer, doc_id
- Admin view in settings page

**4.7 — Export Answers**
- "Export as PDF" button on chat responses
- PDF includes: query, answer, citations, document name, timestamp

**4.8 — Performance Hardening**
- Background task queue (Celery + Redis) for document processing jobs
- Streaming responses for LLM answers (Server-Sent Events)
- Caching: Redis cache for repeated queries on same doc

---

## Phase 5 — Legal Doc Drafting Module (Future Scope)
**Goal**: Implement the document drafting module (Phase 4 shell becomes functional).

**Duration estimate**: 2–3 weeks

**5.1 — Drafting Agent**
- New `DraftingAgent` in Pydantic AI
- Takes: document type, party names, key terms
- Generates: structured draft with clause-by-clause breakdown
- Re-uses PII replacement for party aliases

**5.2 — Drafting Editor UI**
- Rich text editor (Tiptap or Quill)
- Clause-level regeneration: click a clause → "Regenerate this clause"
- Version history
- Export as DOCX / PDF

**5.3 — Template Library**
- Pre-built templates: NDA, MSA, SOW, Employment Agreement, IP Assignment
- Community templates (future)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                          │
│  Upload UI │ Document Library │ Chat Panel │ Info Pages      │
│  Settings  │ Drafting Shell   │ Floating Bot               │
└─────────────────────────────┬───────────────────────────────┘
                              │ REST + SSE
┌─────────────────────────────▼───────────────────────────────┐
│                   FastAPI Backend                             │
│                                                              │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ Orchestrator │  │  Ingestion     │  │  Retrieval     │  │
│  │   Agent      │  │  Agent         │  │  Agent         │  │
│  └──────┬───────┘  └────────────────┘  └────────────────┘  │
│         │          ┌────────────────┐  ┌────────────────┐  │
│         └─────────►│  PII Agent     │  │ Summarization  │  │
│                    └────────────────┘  │  Agent         │  │
│                                        └────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  FastMCP Server                       │  │
│  │  document_tools │ query_tools │ summary_tools         │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────────┐
│ PostgreSQL  │  │    Qdrant       │
│  Documents  │  │  Vector Store   │
│  PII Maps   │  │  (per org)      │
│  Org/User   │  └─────────────────┘
│  Audit Log  │
└──────┬──────┘
       │
┌──────▼──────┐
│    Redis    │
│ PII Hot Map │
│ Query Cache │
│ Session Ctx │
└─────────────┘
```

---

## Verification Plan

### Phase 1
- Unit tests for each agent (pytest + pytest-asyncio)
- API integration tests (httpx TestClient)
- Manual: Upload a PDF → verify PII is masked → ask a query → verify de-anonymized response
- Manual: Risk score is returned with reasonable breakdown

### Phase 2
- Manual UI walkthrough: upload → index → query cycle
- Test floating chatbot context enrichment with page navigation
- Cross-browser check (Chrome, Firefox, Safari)

### Phase 3–5
- E2E tests with Playwright
- Performance benchmark: p95 query latency < 3s for cached, < 8s for cold
- RAGAS score benchmarks on a fixed test set

---

## Repo Structure (Final)

```
droit/
├── backend/          # FastAPI + Agents + MCP (Phase 1)
├── frontend/         # Next.js app (Phase 2)
├── docs/             # MDX content for blog + legal guides
├── scripts/          # Dev utilities, seed scripts
├── docker-compose.yml
└── README.md
```
