"""Optional structured LLM enrichment for heuristic document risk scores."""

from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from ..generation import AnswerGenerator
from ..retrieval import RetrievedChunk
from .scorer import RiskAssessment


class RiskEnrichment(BaseModel):
    score_delta: float = Field(ge=-20, le=20)
    findings: list[str] = Field(default_factory=list, max_length=8)
    confidence: float = Field(ge=0, le=1)


class RiskEnricher(Protocol):
    async def enrich(self, text: str, baseline: RiskAssessment) -> RiskAssessment: ...


class LLMRiskEnricher:
    def __init__(self, generator: AnswerGenerator) -> None:
        self._generator = generator

    async def enrich(self, text: str, baseline: RiskAssessment) -> RiskAssessment:
        prompt = (
            "Assess the legal risk of this anonymized contract using the baseline "
            "assessment below. Return only valid JSON with exactly these fields: "
            "score_delta (number from -20 to 20), findings (array of at most 8 "
            "short strings), and confidence (number from 0 to 1). Do not reveal "
            "or infer anonymized personal data.\n\n"
            f"Baseline: {json.dumps(baseline.breakdown, sort_keys=True)}\n"
            f"Document:\n{text}"
        )
        generated = await self._generator.generate(
            prompt,
            [
                RetrievedChunk(
                    chunk_id=_zero_uuid(),
                    document_id=_zero_uuid(),
                    chunk_index=0,
                    text=text,
                )
            ],
        )
        enrichment = _parse_enrichment(generated.answer)
        findings = list(baseline.breakdown.get("findings", []))
        findings.extend(
            {
                "category": "llm_review",
                "label": finding,
                "severity": "medium",
                "score": 0.0,
                "start": None,
                "end": None,
            }
            for finding in enrichment.findings
        )
        breakdown = {
            **baseline.breakdown,
            "findings": findings,
            "llm_score_delta": enrichment.score_delta,
            "llm_findings": enrichment.findings,
            "llm_confidence": enrichment.confidence,
            "llm_status": "applied",
        }
        return RiskAssessment(
            score=round(min(100, max(0, baseline.score + enrichment.score_delta)), 2),
            breakdown=breakdown,
        )


def _parse_enrichment(answer: str) -> RiskEnrichment:
    candidate = answer.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate).strip()
    try:
        return RiskEnrichment.model_validate_json(candidate)
    except (ValidationError, ValueError) as exc:
        raise ValueError("The language model returned invalid risk JSON") from exc


def _zero_uuid():
    from uuid import UUID

    return UUID(int=0)