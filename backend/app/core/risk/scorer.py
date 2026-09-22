"""Explainable baseline risk scoring for legal documents."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RiskWeights:
    """Per-category point values applied before the 0-100 cap."""

    missing_clause: float = 8.0
    asymmetric_term: float = 5.0
    auto_renewal: float = 15.0
    jurisdiction: float = 15.0
    pii_density: float = 10.0
    max_asymmetry: float = 20.0


@dataclass(frozen=True)
class RiskFinding:
    category: str
    label: str
    severity: Severity
    score: float
    start: int | None = None
    end: int | None = None


@dataclass(frozen=True)
class RiskAssessment:
    score: float
    breakdown: dict[str, object]


@dataclass(frozen=True)
class _ClauseRule:
    severity: Severity
    patterns: tuple[str, ...]


_EXPECTED_CLAUSES: dict[str, _ClauseRule] = {
    "indemnification": _ClauseRule(
        Severity.HIGH, (r"\bindemnif(?:y|ies|ication)\b", r"\bhold harmless\b")
    ),
    "limitation_of_liability": _ClauseRule(
        Severity.HIGH,
        (
            r"\blimitation of liability\b",
            r"\bliability (?:is|shall be) limited\b",
            r"\bliability cap\b",
        ),
    ),
    "confidentiality": _ClauseRule(
        Severity.HIGH, (r"\bconfidential(?:ity)?\b", r"\bnon-disclosure\b")
    ),
    "data_protection": _ClauseRule(
        Severity.HIGH,
        (r"\bdata protection\b", r"\bpersonal data\b", r"\bgdpr\b", r"\bprivacy policy\b"),
    ),
    "governing_law": _ClauseRule(
        Severity.HIGH, (r"\bgoverning law\b", r"\bjurisdiction\b")
    ),
    "termination": _ClauseRule(
        Severity.MEDIUM, (r"\bterminat(?:e|es|ion)\b", r"\bexpir(?:y|ation)\b")
    ),
    "payment_terms": _ClauseRule(
        Severity.MEDIUM,
        (r"\bpayment terms?\b", r"\binvoice[sd]?\b", r"\bfees? (?:are|shall)\b"),
    ),
    "dispute_resolution": _ClauseRule(
        Severity.MEDIUM,
        (r"\bdispute resolution\b", r"\barbitration\b", r"\bmediation\b"),
    ),
    "ip_ownership": _ClauseRule(
        Severity.MEDIUM,
        (
            r"\bintellectual property\b",
            r"\bworks? made for hire\b",
            r"\bownership of (?:the )?deliverables\b",
        ),
    ),
    "assignment": _ClauseRule(
        Severity.LOW, (r"\bassign(?:ment|s|ed)?\b", r"\bsublicen[cs]e\b")
    ),
}

_ASYMMETRIC_PATTERNS = (
    r"\bsole discretion\b",
    r"\bwithout cause\b",
    r"\bunilateral(?:ly)?\b",
    r"\bone party may\b",
    r"\bat any time without notice\b",
    r"\bwaives? any right\b",
)
_AUTO_RENEWAL_PATTERNS = (
    r"\bautomatic(?:ally)? renew",
    r"\bauto-renew",
    r"\bsuccessive renewal terms?\b",
    r"\brenews? unless (?:either party |a party )?(?:gives|provides) notice\b",
)


def score_document_risk(
    text: str, *, pii_density: float = 0.0, weights: RiskWeights | None = None
) -> RiskAssessment:
    """Score common contract risks from anonymized text on a 0-100 scale."""
    applied = weights or RiskWeights()
    findings: list[RiskFinding] = []

    missing_clauses = [
        clause
        for clause, rule in _EXPECTED_CLAUSES.items()
        if not any(
            re.search(pattern, text, flags=re.IGNORECASE) for pattern in rule.patterns
        )
    ]
    findings.extend(
        RiskFinding(
            category="missing_clause",
            label=clause,
            severity=_EXPECTED_CLAUSES[clause].severity,
            score=applied.missing_clause,
        )
        for clause in missing_clauses
    )

    asymmetric = _locate(text, _ASYMMETRIC_PATTERNS)
    asymmetry_budget = min(
        applied.max_asymmetry, applied.asymmetric_term * len(asymmetric)
    )
    per_asymmetry = asymmetry_budget / len(asymmetric) if asymmetric else 0.0
    findings.extend(
        RiskFinding(
            category="asymmetric_term",
            label=phrase,
            severity=Severity.MEDIUM,
            score=round(per_asymmetry, 2),
            start=start,
            end=end,
        )
        for phrase, start, end in asymmetric
    )

    auto_renewal = _locate(text, _AUTO_RENEWAL_PATTERNS)
    per_renewal = applied.auto_renewal / len(auto_renewal) if auto_renewal else 0.0
    findings.extend(
        RiskFinding(
            category="auto_renewal",
            label=phrase,
            severity=Severity.HIGH,
            score=round(per_renewal, 2),
            start=start,
            end=end,
        )
        for phrase, start, end in auto_renewal
    )

    if "governing_law" in missing_clauses:
        findings.append(
            RiskFinding(
                category="jurisdiction",
                label="No governing law or jurisdiction is stated",
                severity=Severity.HIGH,
                score=applied.jurisdiction,
            )
        )

    pii_score = min(applied.pii_density, max(0.0, pii_density) * 1000)
    if pii_score > 0:
        findings.append(
            RiskFinding(
                category="pii_density",
                label=f"{pii_density:.2%} of the document is personal data",
                severity=(
                    Severity.HIGH if pii_score >= applied.pii_density else Severity.MEDIUM
                ),
                score=round(pii_score, 2),
            )
        )

    return RiskAssessment(
        score=round(min(100.0, sum(finding.score for finding in findings)), 2),
        breakdown=build_breakdown(findings, applied),
    )


def build_breakdown(
    findings: list[RiskFinding], weights: RiskWeights
) -> dict[str, object]:
    """Serialize findings with per-category totals and the weights that produced them."""
    category_scores: dict[str, float] = {}
    for finding in findings:
        category_scores[finding.category] = round(
            category_scores.get(finding.category, 0.0) + finding.score, 2
        )
    return {
        "missing_clauses": [
            finding["label"]
            for finding in (
                {**asdict(finding), "severity": finding.severity.value}
                for finding in findings
            )
            if finding["category"] == "missing_clause"
        ],
        "missing_clause_score": category_scores.get("missing_clause", 0.0),
        "asymmetric_terms": [
            finding.label
            for finding in findings
            if finding.category == "asymmetric_term"
        ],
        "asymmetry_score": category_scores.get("asymmetric_term", 0.0),
        "jurisdiction_score": category_scores.get("jurisdiction", 0.0),
        "auto_renewal_terms": [
            finding.label
            for finding in findings
            if finding.category == "auto_renewal"
        ],
        "auto_renewal_score": category_scores.get("auto_renewal", 0.0),
        "pii_score": category_scores.get("pii_density", 0.0),
        "findings": [
            {**asdict(finding), "severity": finding.severity.value}
            for finding in findings
        ],
        "category_scores": category_scores,
        "weights": asdict(weights),
    }


def _locate(text: str, patterns: tuple[str, ...]) -> list[tuple[str, int, int]]:
    """Return the first occurrence of each matching pattern with its character span."""
    located: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is None:
            continue
        phrase = match.group(0).strip()
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        located.append((phrase, match.start(), match.end()))
    return located