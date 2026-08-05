"""
main.py
--------
Droit.ai — CLI Entry Point

Usage
-----
  # Ingest a new document and ask a question:
  python main.py --file path/to/contract.txt --query "What is the effective date?"

  # Ask a question against an already-indexed document store (skip re-ingestion):
  python main.py --query "Who are the parties?" --load-existing

Options
-------
  --file            Path to the legal document to ingest (required unless --load-existing)
  --query           Question to ask the pipeline (required)
  --load-existing   Skip ingestion and load the existing ChromaDB index from disk
  --top-k           Number of final chunks passed to the LLM (default: 3)
  --no-generate     Run retrieval only; skip LLM generation (useful for debugging)

Logging
-------
  Set LOG_LEVEL=DEBUG in .env or the shell for verbose output.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Logging setup — must happen before any droit imports so all loggers inherit
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("droit.main")

# ---------------------------------------------------------------------------
# Droit pipeline imports
# ---------------------------------------------------------------------------
from droit.chunking.splitter import split_document
from droit.embedding.indexer import build_index, load_index
from droit.generation.generator import generate_answer
from droit.ingestion.loader import load_document
from droit.ingestion.metadata_extractor import extract_metadata
from droit.retrieval.retriever import retrieve_and_rerank


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def run_pipeline(
    file_path: str | None,
    query: str,
    load_existing: bool,
    top_k: int,
    no_generate: bool,
) -> None:
    """
    Orchestrate the full Droit.ai RAG pipeline.

    Steps:
      1. Load document (unless --load-existing)
      2. Extract metadata
      3. Split into chunks
      4. Embed and index into ChromaDB  (or load existing index)
      5. Retrieve + rerank
      6. Generate LLM answer
    """

    # ---- Stage 1–4: Ingestion (skipped if loading existing index) ----------
    if load_existing:
        logger.info("Skipping ingestion — loading existing ChromaDB index.")
        vectorstore = load_index()
    else:
        if not file_path:
            logger.error("--file is required when not using --load-existing.")
            sys.exit(1)

        logger.info("=" * 60)
        logger.info("STAGE 1 | Loading document: %s", file_path)
        raw_text = load_document(file_path)

        logger.info("STAGE 2 | Extracting metadata …")
        metadata = extract_metadata(raw_text, source_file=file_path)
        _print_metadata(metadata)

        logger.info("STAGE 3 | Splitting document into chunks …")
        documents = split_document(raw_text, metadata)
        logger.info("         → %d chunks created.", len(documents))

        logger.info("STAGE 4 | Embedding and indexing into ChromaDB …")
        vectorstore = build_index(documents)

    # ---- Stage 5: Retrieval + Reranking ------------------------------------
    logger.info("=" * 60)
    logger.info("STAGE 5 | Retrieving context for query: '%s'", query)
    top_chunks = retrieve_and_rerank(query, vectorstore, top_k_rerank=top_k)

    if no_generate:
        logger.info("--no-generate flag set. Skipping LLM generation.")
        print("\n--- TOP RETRIEVED CHUNKS ---")
        for i, doc in enumerate(top_chunks, start=1):
            print(f"\n[Chunk {i}] ID: {doc.metadata.get('chunk_id')}")
            print(doc.page_content[:300], "...")
        return

    # ---- Stage 6: LLM Generation ------------------------------------------
    logger.info("=" * 60)
    logger.info("STAGE 6 | Generating answer via Groq …")
    answer = generate_answer(query, top_chunks)

    print("\n" + "=" * 60)
    print("DROIT.AI — FINAL ANSWER")
    print("=" * 60)
    print(f"Query : {query}")
    print("-" * 60)
    print(answer)
    print("=" * 60)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_metadata(metadata: dict) -> None:
    print("\n--- Extracted Document Metadata ---")
    for key, value in metadata.items():
        print(f"  {key:<22}: {value}")
    print()


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="droit",
        description="Droit.ai — Legal Document RAG Pipeline",
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to the legal document (.txt) to ingest.",
    )
    parser.add_argument(
        "--query",
        required=True,
        metavar="QUESTION",
        help="Natural-language question to ask the pipeline.",
    )
    parser.add_argument(
        "--load-existing",
        action="store_true",
        default=False,
        help="Load the existing ChromaDB index instead of re-indexing.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        metavar="N",
        help="Number of reranked chunks passed to the LLM (default: 3).",
    )
    parser.add_argument(
        "--no-generate",
        action="store_true",
        default=False,
        help="Skip LLM generation; print retrieved chunks only.",
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()

    run_pipeline(
        file_path=args.file,
        query=args.query,
        load_existing=args.load_existing,
        top_k=args.top_k,
        no_generate=args.no_generate,
    )
