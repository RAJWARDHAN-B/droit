"""Deterministic PII aliases built from Presidio recognizer results."""

from __future__ import annotations

import importlib.util
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from presidio_analyzer import AnalyzerEngine

logger = logging.getLogger(__name__)

from cryptography.fernet import Fernet, InvalidToken
from presidio_analyzer import RecognizerResult
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    InAadhaarRecognizer,
    PhoneRecognizer,
    UsSsnRecognizer,
)

from ...config import Settings

_ENTITY_ALIASES = {
    "CREDIT_CARD": "FINANCIAL",
    "EMAIL_ADDRESS": "EMAIL",
    "IBAN_CODE": "FINANCIAL",
    "IN_AADHAAR": "AADHAAR",
    "PHONE_NUMBER": "PHONE",
    "US_SSN": "SSN",
    "PERSON": "PERSON",
    "ORGANIZATION": "ORG",
    "NRP": "NRP",
    "LOCATION": "LOCATION",
}

# Generic dates are excluded: notice periods and durations carry legal meaning
# and are not personally identifying.
_NER_ENTITIES = ("PERSON", "ORGANIZATION", "NRP", "LOCATION")

# Instrument names such as "Master Services Agreement" identify the document,
# not a party, so masking them would destroy the document's meaning.
_LEGAL_INSTRUMENT_NOUNS = frozenset(
    {
        "addendum",
        "agreement",
        "amendment",
        "annex",
        "appendix",
        "clause",
        "contract",
        "covenant",
        "deed",
        "exhibit",
        "indenture",
        "lease",
        "license",
        "memorandum",
        "policy",
        "schedule",
        "terms",
        "waiver",
    }
)

_RECOGNIZERS = (
    EmailRecognizer(),
    PhoneRecognizer(),
    UsSsnRecognizer(),
    InAadhaarRecognizer(),
    CreditCardRecognizer(),
    IbanRecognizer(),
)

_MIN_NER_SCORE = 0.4


@dataclass(frozen=True)
class PIIMatch:
    alias: str
    entity_type: str
    original_value: str


def anonymize_text(text: str) -> tuple[str, list[PIIMatch]]:
    """Replace detected PII with stable aliases ordered by first occurrence."""
    results = _non_overlapping_results(_analyze(text))
    counters: defaultdict[str, int] = defaultdict(int)
    aliases: dict[tuple[str, str], str] = {}
    mappings: list[PIIMatch] = []
    pieces: list[str] = []
    cursor = 0

    for result in results:
        original = text[result.start : result.end]
        alias_type = _ENTITY_ALIASES[result.entity_type]
        identity = (alias_type, original.casefold())
        alias = aliases.get(identity)
        if alias is None:
            counters[alias_type] += 1
            alias = f"[{alias_type}_{counters[alias_type]}]"
            aliases[identity] = alias
            mappings.append(
                PIIMatch(
                    alias=alias,
                    entity_type=result.entity_type,
                    original_value=original,
                )
            )
        pieces.extend((text[cursor : result.start], alias))
        cursor = result.end

    pieces.append(text[cursor:])
    return "".join(pieces), mappings


def restore_text(text: str, replacements: dict[str, str]) -> str:
    """Replace complete anonymization aliases with their original values."""
    if not replacements:
        return text
    aliases = sorted(replacements, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(alias) for alias in aliases))
    return pattern.sub(lambda match: replacements[match.group(0)], text)


def encrypt_value(value: str, settings: Settings) -> bytes:
    return _cipher(settings).encrypt(value.encode("utf-8"))


def decrypt_value(value: bytes, settings: Settings) -> str:
    try:
        return _cipher(settings).decrypt(value).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt PII mapping with the configured key") from exc


def _analyze(text: str) -> list[RecognizerResult]:
    results: list[RecognizerResult] = []
    for recognizer in _RECOGNIZERS:
        results.extend(
            recognizer.analyze(
                text,
                entities=recognizer.supported_entities,
                nlp_artifacts=None,
            )
        )
    results.extend(_analyze_named_entities(text))
    return [result for result in results if result.entity_type in _ENTITY_ALIASES]


def _analyze_named_entities(text: str) -> list[RecognizerResult]:
    """Detect names, organizations, and locations when an NER model is installed."""
    engine = _ner_engine()
    if engine is None:
        return []
    results = engine.analyze(text=text, language="en", entities=list(_NER_ENTITIES))
    return [
        result
        for result in results
        if result.score >= _MIN_NER_SCORE
        and not _is_common_word(text[result.start : result.end], text)
        and not _is_legal_instrument(text[result.start : result.end])
    ]


def _is_legal_instrument(candidate: str) -> bool:
    words = re.findall(r"[\w']+", candidate.casefold())
    return bool(words) and words[-1] in _LEGAL_INSTRUMENT_NOUNS


def _is_common_word(candidate: str, text: str) -> bool:
    """Reject proper-noun matches that also appear lowercased in the same document."""
    normalized = candidate.strip()
    if not normalized or not normalized[0].isupper():
        return False
    return re.search(rf"\b{re.escape(normalized.lower())}\b", text) is not None


@lru_cache(maxsize=1)
def _ner_engine() -> AnalyzerEngine | None:
    from ...config import get_settings

    settings = get_settings()
    model_name = settings.pii_ner_model
    # Presidio downloads absent spaCy models on load, so verify installation
    # first to avoid a blocking network call at request time.
    if importlib.util.find_spec(model_name) is None:
        return _missing_ner_model(model_name, settings)
    try:
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": model_name}],
                "ner_model_configuration": {
                    "model_to_presidio_entity_mapping": {
                        "PER": "PERSON",
                        "PERSON": "PERSON",
                        "NORP": "NRP",
                        "ORG": "ORGANIZATION",
                        "LOC": "LOCATION",
                        "GPE": "LOCATION",
                        "FAC": "LOCATION",
                    },
                    # Retained verbatim: these carry legal meaning and are not
                    # personally identifying.
                    "labels_to_ignore": [
                        "O",
                        "DATE",
                        "TIME",
                        "MONEY",
                        "PERCENT",
                        "CARDINAL",
                        "ORDINAL",
                        "QUANTITY",
                        "LAW",
                        "PRODUCT",
                        "EVENT",
                        "WORK_OF_ART",
                        "LANGUAGE",
                    ],
                },
            }
        )
        return AnalyzerEngine(
            nlp_engine=provider.create_engine(), supported_languages=["en"]
        )
    except Exception:
        return _missing_ner_model(model_name, settings)


def _missing_ner_model(model_name: str, settings: Settings) -> None:
    if settings.environment.lower() == "production":
        raise RuntimeError(
            f"spaCy model '{model_name}' is required to anonymize names and "
            "organizations. Install it with: uv pip install -r "
            "backend/requirements.txt"
        )
    logger.warning(
        "spaCy model '%s' unavailable; names and organizations will NOT be "
        "anonymized and may be sent to LLM providers. Install it with: "
        "uv pip install -r backend/requirements.txt",
        model_name,
    )
    return None


def _non_overlapping_results(
    results: list[RecognizerResult],
) -> list[RecognizerResult]:
    ranked = sorted(
        results,
        key=lambda result: (result.start, -result.score, -(result.end - result.start)),
    )
    accepted: list[RecognizerResult] = []
    for result in ranked:
        if result.start == result.end:
            continue
        if accepted and result.start < accepted[-1].end:
            continue
        accepted.append(result)
    return accepted


def _cipher(settings: Settings) -> Fernet:
    configured_key = settings.pii_encryption_key
    if configured_key is not None:
        return Fernet(configured_key.get_secret_value().encode("ascii"))
    if settings.environment.lower() == "production":
        raise RuntimeError("DROIT_PII_ENCRYPTION_KEY is required in production")
    return Fernet(_development_key(settings.storage_root))


def _development_key(storage_root: Path) -> bytes:
    key_path = storage_root / ".pii.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return key_path.read_bytes().strip()

    key = Fernet.generate_key()
    with os.fdopen(descriptor, "wb") as key_file:
        key_file.write(key)
    return key