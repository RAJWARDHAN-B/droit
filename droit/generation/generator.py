"""
droit/generation/generator.py
------------------------------
Stage 6: LLM Answer Generation (via Groq)

Takes the top reranked chunks and a user query, formats a structured
prompt with rich context, and calls the Groq API to produce a grounded,
hallucination-resistant legal answer.

The system prompt instructs the model to cite only what is in the provided
context — never to invent facts — which is critical for legal applications.
"""

from __future__ import annotations

import logging

from groq import Groq
from langchain_core.documents import Document

from droit.config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client singleton
# ---------------------------------------------------------------------------
_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. "
                "Add it to your .env file: GROQ_API_KEY=gsk_..."
            )
        _client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized (model: %s).", GROQ_MODEL)
    return _client


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are Droit, an expert AI legal assistant. "
    "Answer the user's question using ONLY the document context snippets provided below. "
    "When citing facts, reference the relevant contract type or parties. "
    "If the information is not present in the context, respond with: "
    "'I cannot find this information in the provided document.' "
    "Never hallucinate, fabricate clauses, or assume facts not in the context."
)


def _format_context(chunks: list[Document]) -> str:
    """Format reranked chunks into a structured context block for the prompt."""
    parts: list[str] = []
    for i, doc in enumerate(chunks, start=1):
        m = doc.metadata
        part = (
            f"--- CONTEXT SNIPPET {i} ---\n"
            f"Source File     : {m.get('source_file', 'unknown')}\n"
            f"Contract Type   : {m.get('doc_type', 'unknown')}\n"
            f"Primary Parties : {', '.join(m.get('primary_parties', []))}\n"
            f"Effective Date  : {m.get('effective_date', 'unknown')}\n"
            f"Chunk ID        : {m.get('chunk_id', 'unknown')}\n\n"
            f"{doc.page_content}\n"
        )
        parts.append(part)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_answer(query: str, context_chunks: list[Document]) -> str:
    """
    Generate a grounded legal answer using Groq LLM.

    Parameters
    ----------
    query : str
        The user's natural-language question.
    context_chunks : list[Document]
        Top reranked chunks from ``retriever.retrieve_and_rerank()``.

    Returns
    -------
    str
        The LLM-generated answer, grounded in the provided context.

    Raises
    ------
    EnvironmentError
        If GROQ_API_KEY is missing.
    groq.APIError
        On upstream Groq API failures.
    """
    if not context_chunks:
        logger.warning("No context chunks provided — returning fallback message.")
        return "I cannot find this information in the provided document."

    formatted_context = _format_context(context_chunks)

    user_prompt = (
        f"DOCUMENT CONTEXT:\n"
        f"{formatted_context}\n"
        f"USER QUESTION:\n"
        f"{query}\n"
    )

    logger.info("Sending query to Groq (model=%s) …", GROQ_MODEL)

    response = _get_client().chat.completions.create(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
    )

    answer: str = response.choices[0].message.content
    logger.info("Answer generated (%d characters).", len(answer))
    return answer
