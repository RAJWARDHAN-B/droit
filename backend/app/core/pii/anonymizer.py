"""Deterministic PII aliases built from Presidio recognizer results."""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

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
}

_RECOGNIZERS = (
    EmailRecognizer(),
    PhoneRecognizer(),
    UsSsnRecognizer(),
    InAadhaarRecognizer(),
    CreditCardRecognizer(),
    IbanRecognizer(),
)


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
    return [result for result in results if result.entity_type in _ENTITY_ALIASES]


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