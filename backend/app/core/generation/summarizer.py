"""Legal and layman document summaries built on the provider-agnostic generator."""

from __future__ import annotations

from enum import Enum

from ..retrieval import RetrievedChunk
from .generator import AnswerGenerator, GeneratedAnswer


class SummaryStyle(str, Enum):
    LEGAL = "legal"
    LAYMAN = "layman"


_SHARED_RULES = (
    "Summarize only what the document states and never invent facts. "
    "Bracketed placeholders such as [PERSON_1] are redacted personal data; "
    "reproduce them verbatim and never guess the underlying value."
)

_SYSTEM_PROMPTS = {
    SummaryStyle.LEGAL: (
        "You are Droit, a legal analyst writing for practising lawyers. "
        "Preserve defined terms, clause numbering, and statutory references exactly as written. "
        "Structure the summary as: Parties, Term, Key obligations, Liability and indemnity, "
        "Termination, Governing law, Notable deviations. " + _SHARED_RULES
    ),
    SummaryStyle.LAYMAN: (
        "You are Droit, explaining a legal document to someone with no legal training. "
        "Use short plain-English sentences, avoid Latin and legal jargon, and translate any "
        "term you must keep. Structure the summary as: What this document is, Who is involved, "
        "What each side must do, What it costs, How it ends, What to watch out for. "
        + _SHARED_RULES
    ),
}

_INSTRUCTIONS = {
    SummaryStyle.LEGAL: "Produce the legal summary of the document in the context passage.",
    SummaryStyle.LAYMAN: "Produce the plain-English summary of the document in the context passage.",
}

MAX_SUMMARY_INPUT_CHARS = 24_000


async def summarize_document(
    text: str,
    style: SummaryStyle,
    generator: AnswerGenerator,
    *,
    document_id,
) -> GeneratedAnswer:
    """Summarize anonymized document text in the requested style."""
    if not text.strip():
        raise ValueError("Cannot summarize an empty document")
    chunk = RetrievedChunk(
        chunk_id=document_id,
        document_id=document_id,
        chunk_index=0,
        text=text[:MAX_SUMMARY_INPUT_CHARS],
    )
    return await generator.generate(
        _INSTRUCTIONS[style], [chunk], system_prompt=_SYSTEM_PROMPTS[style]
    )
