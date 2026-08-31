"""Explainable baseline risk scoring for legal documents."""

from __future__ import annotations

import re
from dataclasses import dataclass


_EXPECTED_CLAUSES = {
    "indemnification": (r"\bindemnif(?:y|ication)\b",),
    "limitation_of_liability": (
        r"\blimitation of liability\b",
        r"\bliability (?:is|shall be) limited\b",
    ),
    "termination": (r"\bterminat(?:e|ion)\b",),
    "governing_law": (r"\bgoverning law\b", r"\bjurisdiction\b"),
}
_ASYMMETRIC_PATTERNS = (
    r"\bsole discretion\b",
    r"\bwithout cause\b",
    r"\bunilateral(?:ly)?\b",
    r"\bone party may\b",
)
_AUTO_RENEWAL_PATTERNS = (
    r"\bautomatic(?:ally)? renew",
    r"\bauto-renew",
    r"\bsuccessive renewal terms?\b",
)


@dataclass(frozen=True)
class RiskAssessment:
    score: float
    breakdown: dict[str, object]


def score_document_risk(text: str, *, pii_density: float = 0.0) -> RiskAssessment:
    """Score common contract risks from anonymized text on a 0-100 scale."""
    normalized = text.casefold()
    missing_clauses = [
        clause
        for clause, patterns in _EXPECTED_CLAUSES.items()
        if not any(re.search(pattern, normalized) for pattern in patterns)
    ]
    asymmetric_terms = _matched_phrases(normalized, _ASYMMETRIC_PATTERNS)
    auto_renewal_terms = _matched_phrases(normalized, _AUTO_RENEWAL_PATTERNS)

    missing_clause_score = 10 * len(missing_clauses)
    asymmetry_score = min(20, 10 * len(asymmetric_terms))
    jurisdiction_score = 15 if "governing_law" in missing_clauses else 0
    auto_renewal_score = 15 if auto_renewal_terms else 0
    pii_score = min(10.0, max(0.0, pii_density) * 1000)
    total = min(
        100.0,
        missing_clause_score
        + asymmetry_score
        + jurisdiction_score
        + auto_renewal_score
        + pii_score,
    )

    return RiskAssessment(
        score=round(total, 2),
        breakdown={
            "missing_clauses": missing_clauses,
            "missing_clause_score": missing_clause_score,
            "asymmetric_terms": asymmetric_terms,
            "asymmetry_score": asymmetry_score,
            "jurisdiction_score": jurisdiction_score,
            "auto_renewal_terms": auto_renewal_terms,
            "auto_renewal_score": auto_renewal_score,
            "pii_score": round(pii_score, 2),
        },
    )


def _matched_phrases(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [
        match.group(0)
        for pattern in patterns
        if (match := re.search(pattern, text)) is not None
    ]