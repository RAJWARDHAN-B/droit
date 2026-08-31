"""Tests for deterministic aliases and encrypted PII values."""

import pytest

from backend.app.config import Settings
from backend.app.core.pii import anonymize_text, decrypt_value, encrypt_value


def test_repeated_pii_reuses_deterministic_alias() -> None:
    anonymized, mappings = anonymize_text(
        "Email jane@example.com, then email jane@example.com again."
    )

    assert anonymized == "Email [EMAIL_1], then email [EMAIL_1] again."
    assert len(mappings) == 1
    assert mappings[0].alias == "[EMAIL_1]"
    assert mappings[0].entity_type == "EMAIL_ADDRESS"
    assert mappings[0].original_value == "jane@example.com"


def test_encrypted_value_round_trip_uses_local_development_key(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)

    encrypted = encrypt_value("jane@example.com", settings)

    assert encrypted != b"jane@example.com"
    assert decrypt_value(encrypted, settings) == "jane@example.com"
    assert (tmp_path / ".pii.key").stat().st_mode & 0o777 == 0o600


def test_production_requires_explicit_encryption_key(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path, environment="production")

    with pytest.raises(RuntimeError, match="DROIT_PII_ENCRYPTION_KEY"):
        encrypt_value("jane@example.com", settings)