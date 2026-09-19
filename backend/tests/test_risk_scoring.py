"""Tests for explainable document risk scoring."""

import pytest

from backend.app.core.risk import LLMRiskEnricher, score_document_risk
from backend.app.core.generation import GeneratedAnswer


class StubGenerator:
    async def generate(self, question, chunks):
        return GeneratedAnswer(
            answer='{"score_delta": 12, "findings": ["Missing audit rights"], "confidence": 0.8}',
            provider="stub",
            model="stub",
        )


def test_balanced_contract_has_lower_risk_than_unilateral_auto_renewal() -> None:
    balanced = score_document_risk(
        "The parties provide mutual indemnification. The limitation of liability "
        "applies equally. Either party may terminate. The governing law is Delaware."
    )
    risky = score_document_risk(
        "The agreement automatically renews. One party may terminate without cause "
        "in its sole discretion.",
        pii_density=0.02,
    )

    assert balanced.score == 0
    assert risky.score > balanced.score
    assert risky.score == 90
    assert risky.breakdown["missing_clauses"] == [
        "indemnification",
        "limitation_of_liability",
        "governing_law",
    ]
    assert risky.breakdown["auto_renewal_score"] == 15


def test_pii_density_is_capped_and_cannot_reduce_score() -> None:
    assessment = score_document_risk("", pii_density=1.0)

    assert assessment.breakdown["pii_score"] == 10
    assert assessment.score == 65


@pytest.mark.asyncio
async def test_llm_enrichment_adds_validated_findings_to_baseline() -> None:
    baseline = score_document_risk("The governing law is Delaware.")

    enriched = await LLMRiskEnricher(StubGenerator()).enrich(
        "The governing law is Delaware.", baseline
    )

    assert enriched.score == baseline.score + 12
    assert enriched.breakdown["llm_findings"] == ["Missing audit rights"]
    assert enriched.breakdown["llm_confidence"] == 0.8