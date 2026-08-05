"""
droit/config.py
---------------
Central configuration for the Droit.ai pipeline.
All tuneable parameters and environment variables are defined here.
Import this module in any pipeline stage instead of hardcoding values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (two levels up from this file)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CHROMA_PERSIST_DIR: str = str(_ROOT / "chroma_db")   # Persists to disk
CHROMA_COLLECTION_NAME: str = "legal_contracts"

# ---------------------------------------------------------------------------
# Ingestion / Metadata
# ---------------------------------------------------------------------------
# Number of characters from the document header used for entity extraction
METADATA_HEADER_CHARS: int = 1200

# spaCy model to load for NER
SPACY_MODEL: str = "en_core_web_sm"

# Words that spaCy tends to misidentify as ORG/PERSON in legal text
LEGAL_NOISE_WORDS: set[str] = {
    "party",
    "effective date",
    "definitions",
    "suite",
    "deliverable",
    "the service provider",
    "this master services agreement",
    "agreement",
    "section",
    "schedule",
    "exhibit",
    "innovation plaza",
}

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 150
CHUNK_SEPARATORS: list[str] = ["\n\n", "\n", " ", ""]

# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
# "cuda" | "cpu" — set EMBEDDING_DEVICE in .env to override
EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

# ---------------------------------------------------------------------------
# Retrieval / Reranking
# ---------------------------------------------------------------------------
RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
RERANKER_MAX_LENGTH: int = 512
RETRIEVAL_TOP_K: int = 10          # Candidates fetched from vector store
RERANK_TOP_K: int = 3              # Final chunks passed to LLM

# ---------------------------------------------------------------------------
# Generation (Groq)
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE: float = 0.1
