"""
droit/ingestion/metadata_extractor.py
--------------------------------------
Stage 2: Metadata Extraction

Extracts structured, document-level metadata from raw legal text using:
  - spaCy NER  → primary parties (ORG / PERSON entities)
  - Regex       → document type and effective date

The returned ``global_metadata`` dict is attached to every chunk produced by
the chunking stage, enabling filtered vector search by party, doc type, or date.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import spacy

from droit.config import (
    LEGAL_NOISE_WORDS,
    METADATA_HEADER_CHARS,
    SPACY_MODEL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load spaCy model once at import time (module-level singleton)
# ---------------------------------------------------------------------------
try:
    _nlp = spacy.load(SPACY_MODEL)
    logger.info("spaCy model '%s' loaded.", SPACY_MODEL)
except OSError:
    _nlp = None
    logger.warning(
        "spaCy model '%s' not found. Run: python -m spacy download %s",
        SPACY_MODEL,
        SPACY_MODEL,
    )

# ---------------------------------------------------------------------------
# Regex patterns (compiled once)
# ---------------------------------------------------------------------------
_DATE_PATTERN = re.compile(
    r"(\b\d{4}-\d{2}-\d{2}\b"
    r"|\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+\d{4}\b)",
    re.IGNORECASE,
)

_EFFECTIVE_DATE_PATTERN = re.compile(
    r"(?:effective|entered into|dated as of)\s+(?:on\s+)?" + _DATE_PATTERN.pattern,
    re.IGNORECASE,
)

_DOC_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("NDA",                 re.compile(r"non-disclosure agreement|\bnda\b", re.IGNORECASE)),
    ("MSA",                 re.compile(r"master services agreement|\bmsa\b", re.IGNORECASE)),
    ("Employment Agreement",re.compile(r"employment agreement|employment contract", re.IGNORECASE)),
    ("Lease Agreement",     re.compile(r"lease agreement|rental agreement", re.IGNORECASE)),
    ("Partnership Agreement",re.compile(r"partnership agreement", re.IGNORECASE)),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_metadata(text: str, source_file: str = "unknown") -> dict[str, Any]:
    """
    Extract document-level metadata from raw legal text.

    Parameters
    ----------
    text : str
        Full raw text of the legal document.
    source_file : str
        Original file path — stored as metadata for traceability.

    Returns
    -------
    dict
        Keys: doc_type, primary_parties, effective_date,
              total_dates_found, source_file
    """
    parties        = _extract_parties(text[:METADATA_HEADER_CHARS])
    doc_type       = _extract_doc_type(text)
    effective_date, total_dates = _extract_dates(text)

    metadata: dict[str, Any] = {
        "doc_type":        doc_type,
        "primary_parties": parties,
        "effective_date":  effective_date,
        "total_dates_found": total_dates,
        "source_file":     source_file,
    }

    logger.info(
        "Metadata extracted | type=%s | parties=%s | date=%s",
        doc_type, parties, effective_date,
    )
    return metadata


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_parties(header_text: str) -> list[str]:
    """Use spaCy NER on the document header to find primary parties."""
    if _nlp is None:
        logger.warning("spaCy unavailable — skipping party extraction.")
        return []

    doc = _nlp(header_text)
    raw = [ent.text.strip() for ent in doc.ents if ent.label_ in ("ORG", "PERSON")]
    return _clean_parties(raw)


def _clean_parties(raw_entities: list[str]) -> list[str]:
    """
    Filter out noisy spaCy extractions and deduplicate by substring inclusion.
    Longer, more specific names are always preferred over partial matches.
    """
    cleaned: list[str] = []
    for ent in raw_entities:
        ent_clean = ent.strip()
        if (
            len(ent_clean) > 3
            and ent_clean.lower() not in LEGAL_NOISE_WORDS
            and not ent_clean.isupper()          # removes ALL-CAP section headers
        ):
            cleaned.append(ent_clean)

    # Keep the longest form when one entity is a substring of another
    final: list[str] = []
    for candidate in sorted(cleaned, key=len, reverse=True):
        if not any(candidate in existing for existing in final):
            final.append(candidate)
    return final


def _extract_doc_type(text: str) -> str:
    """Match known document-type keywords via regex."""
    for doc_type, pattern in _DOC_TYPE_PATTERNS:
        if pattern.search(text):
            return doc_type
    return "General Legal Document"


def _extract_dates(text: str) -> tuple[str, int]:
    """
    Returns:
      - primary_date : the contextual effective date (or the first date found)
      - total_dates  : total unique dates found in the document
    """
    effective_match = _EFFECTIVE_DATE_PATTERN.search(text)
    all_dates = list(set(_DATE_PATTERN.findall(text)))

    if effective_match:
        primary_date = effective_match.group(1)
    elif all_dates:
        primary_date = all_dates[0]
    else:
        primary_date = "Unknown"

    return primary_date, len(all_dates)
