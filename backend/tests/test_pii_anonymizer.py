"""Tests for deterministic aliases and encrypted PII values."""

import importlib.util

import pytest

from backend.app import config
from backend.app.config import Settings, get_settings
from backend.app.core.pii import anonymize_text, decrypt_value, encrypt_value
from backend.app.core.pii import anonymizer

requires_ner_model = pytest.mark.skipif(
    importlib.util.find_spec(get_settings().pii_ner_model) is None,
    reason="spaCy NER model is not installed",
)


@pytest.fixture
def reset_pii_caches():
    """Isolate tests that alter NER settings from the cached engine."""
    anonymizer._ner_engine.cache_clear()
    config.get_settings.cache_clear()
    yield
    anonymizer._ner_engine.cache_clear()
    config.get_settings.cache_clear()


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


@requires_ner_model
def test_names_organizations_and_locations_are_anonymized() -> None:
    anonymized, mappings = anonymize_text(
        "This agreement is between Acme Corp and Jane Doe. "
        "Governed by the laws of Delaware."
    )

    assert "Jane Doe" not in anonymized
    assert "Acme Corp" not in anonymized
    assert "Delaware" not in anonymized
    assert {mapping.entity_type for mapping in mappings} == {
        "PERSON",
        "ORGANIZATION",
        "LOCATION",
    }


@requires_ner_model
def test_legal_durations_are_not_masked() -> None:
    anonymized, _ = anonymize_text(
        "Either party may terminate with thirty (30) days written notice, "
        "and confidentiality survives for three years."
    )

    assert "thirty (30) days" in anonymized
    assert "three years" in anonymized


def test_missing_ner_model_is_fatal_in_production(monkeypatch, reset_pii_caches) -> None:
    monkeypatch.setenv("DROIT_ENVIRONMENT", "production")
    monkeypatch.setenv("DROIT_PII_NER_MODEL", "en_core_web_absent")

    with pytest.raises(RuntimeError, match="required to anonymize"):
        anonymize_text("This agreement is between Acme Corp and Jane Doe.")


def test_missing_ner_model_degrades_with_warning_in_development(
    monkeypatch, reset_pii_caches, caplog
) -> None:
    monkeypatch.setenv("DROIT_ENVIRONMENT", "development")
    monkeypatch.setenv("DROIT_PII_NER_MODEL", "en_core_web_absent")

    anonymized, mappings = anonymize_text("Contact Jane Doe at jane@example.com.")

    assert "[EMAIL_1]" in anonymized
    assert [mapping.entity_type for mapping in mappings] == ["EMAIL_ADDRESS"]
    assert "will NOT be" in caplog.text


@requires_ner_model
def test_instrument_names_are_preserved_but_parties_are_masked() -> None:
    anonymized, _ = anonymize_text(
        "This Master Services Agreement is entered into between "
        "Globex Industries and John Smith."
    )

    assert "Master Services Agreement" in anonymized
    assert "Globex Industries" not in anonymized
    assert "John Smith" not in anonymized