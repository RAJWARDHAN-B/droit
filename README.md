# Droit.ai

**Droit.ai** is a production-grade, privacy-first Retrieval-Augmented Generation (RAG) platform for legal documents.  
It extracts structured metadata from contracts, indexes them into a persistent vector store, and answers natural-language legal questions using a two-stage retrieval pipeline and a grounded LLM — with strict anti-hallucination guardrails.

---

## Features

- **Modular pipeline** — each stage is an independent, testable Python module
- **Smart metadata extraction** — spaCy NER + regex extracts parties, document type, and effective date from document headers
- **Semantic chunking** — overlapping chunks preserve legal clause boundaries
- **Persistent vector store** — ChromaDB indexes survive process restarts (no re-indexing on every run)
- **Two-stage retrieval** — fast vector search + cross-encoder reranking for high-precision context
- **Grounded LLM answers** — Groq (Llama 3.3 70B) with a strict "cite only what's in the document" system prompt
- **OCR-ready architecture** — the loader module has documented hooks for PDF/image ingestion (next iteration)

---

## Project Structure

```
droit/
├── main.py                         # CLI entry point
├── requirements.txt                # Pinned dependencies
├── .env.example                    # API key & config template
│
└── droit/                          # Core package
    ├── config.py                   # Centralized config (reads .env)
    │
    ├── ingestion/
    │   ├── loader.py               # Stage 1 — Document loading (OCR hook here)
    │   └── metadata_extractor.py  # Stage 2 — NER + regex metadata extraction
    │
    ├── chunking/
    │   └── splitter.py             # Stage 3 — Overlapping text chunking
    │
    ├── embedding/
    │   └── indexer.py              # Stage 4 — HuggingFace embeddings + ChromaDB
    │
    ├── retrieval/
    │   └── retriever.py            # Stage 5 — Vector search + cross-encoder rerank
    │
    └── generation/
        └── generator.py            # Stage 6 — Groq LLM answer generation
```

---

## Pipeline Flow

```
Raw File (.txt)
     │
     ▼
[loader.py]              → raw text string
     │
     ▼
[metadata_extractor.py]  → {doc_type, parties, effective_date, ...}
     │
     ▼
[splitter.py]            → List[LangChain Document]  (chunks + inherited metadata)
     │
     ▼
[indexer.py]             → ChromaDB vectorstore  (persisted to ./chroma_db/)
     │
     ▼
[retriever.py]           → top-k reranked chunks  (vector search → cross-encoder)
     │
     ▼
[generator.py]           → final grounded LLM answer
```

---

## Quick Start

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd droit
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run the pipeline

```bash
# Ingest a document and ask a question
python main.py --file legal.txt --query "What is the effective date?"

# Ask another question (reuse the existing index — no re-indexing)
python main.py --load-existing --query "Who are the primary parties?"

# Debug retrieval without spending API credits
python main.py --file legal.txt --query "What are the confidentiality terms?" --no-generate
```

### CLI Options

| Flag | Description |
|---|---|
| `--file PATH` | Path to the legal document to ingest |
| `--query "..."` | Natural-language question (required) |
| `--load-existing` | Skip ingestion; load the persisted ChromaDB index |
| `--top-k N` | Number of reranked chunks passed to LLM (default: 3) |
| `--no-generate` | Retrieval only — skip LLM generation |

---

## Configuration

All settings are controlled via `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Groq API key from console.groq.com |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | HuggingFace embedding model |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` \| `cuda` \| `mps` |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` |

---

## Roadmap

- [x] Text file ingestion (.txt)
- [x] spaCy NER metadata extraction
- [x] Overlapping chunk splitting
- [x] ChromaDB persistent vector store
- [x] Cross-encoder reranking
- [x] Groq LLM generation with anti-hallucination guardrails
- [x] **OCR support** — PDF, scanned images, DOCX
- [ ] REST API (FastAPI)
- [ ] Multi-document querying with metadata filters
- [ ] RAGAS evaluation pipeline
- [ ] Streamlit / web UI

---

## Tech Stack

| Layer | Technology |
|---|---|
| NLP / NER | spaCy `en_core_web_sm` |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector Store | ChromaDB (disk-persisted) |
| Reranker | `BAAI/bge-reranker-v2-m3` (CrossEncoder) |
| LLM | Groq — Llama 3.3 70B Versatile |
| Config | `python-dotenv` |
