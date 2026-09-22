"""Generate one structured clause through the existing answer provider."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..generation import AnswerGenerator
from ..retrieval import RetrievedChunk


class GeneratedClause(BaseModel):
    heading: str
    body: str
    rationale: str = ""
    risk_notes: list[str] = Field(default_factory=list)


def anonymize_inputs(inputs: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Replace supplied values before they reach a provider and return restorations."""
    aliases: dict[str, str] = {}
    sanitized = dict(inputs)
    for index, (key, value) in enumerate(
        sorted(inputs.items(), key=lambda item: len(item[1]), reverse=True), start=1
    ):
        if not value.strip():
            continue
        alias = f"[INPUT_{index}]"
        sanitized[key] = alias
        aliases[alias] = value
    return sanitized, aliases


def restore_aliases(clause: GeneratedClause, aliases: dict[str, str]) -> GeneratedClause:
    values = clause.model_dump()
    values["body"] = _restore(values["body"], aliases)
    values["rationale"] = _restore(values["rationale"], aliases)
    values["risk_notes"] = [_restore(note, aliases) for note in values["risk_notes"]]
    return GeneratedClause.model_validate(values)


async def generate_clause(
    generator: AnswerGenerator,
    *,
    template_name: str,
    clause_heading: str,
    clause_outline: list[dict[str, Any]],
    inputs: dict[str, str],
    prior_clauses: list[str],
    instruction: str | None = None,
) -> GeneratedClause:
    sanitized, aliases = anonymize_inputs(inputs)
    prompt = {
        "task": "Draft one legally coherent contract clause as JSON.",
        "template": template_name,
        "clause_heading": clause_heading,
        "clause_outline": clause_outline,
        "inputs": sanitized,
        "prior_clauses": prior_clauses,
        "instruction": instruction or "",
        "output_schema": {
            "heading": "string",
            "body": "string",
            "rationale": "string",
            "risk_notes": ["string"],
        },
    }
    response = await generator.generate(
        json.dumps(prompt, ensure_ascii=True),
        [RetrievedChunk(uuid4(), UUID(int=0), 0, json.dumps(prompt), 1.0)],
        system_prompt=(
            "You draft one legal contract clause. Return only valid JSON matching the requested schema. "
            "Use aliases exactly as provided and never infer or restore their original values."
        ),
    )
    parsed = _parse_clause(response.answer)
    return restore_aliases(parsed, aliases)


def _parse_clause(answer: str) -> GeneratedClause:
    candidate = answer.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
    try:
        return GeneratedClause.model_validate_json(candidate)
    except ValueError as exc:
        raise ValueError("The language model returned invalid draft clause JSON") from exc


def _restore(text: str, aliases: dict[str, str]) -> str:
    for alias, value in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(alias, value)
    return text
