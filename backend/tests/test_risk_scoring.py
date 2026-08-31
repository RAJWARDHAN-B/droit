"""Tests for explainable document risk scoring."""

from backend.app.core.risk import score_document_risk


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