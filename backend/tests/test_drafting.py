"""Focused legal drafting generation coverage."""

import pytest

from backend.app.core.drafting import generate_clause
from backend.app.core.generation import GeneratedAnswer


class RecordingGenerator:
    def __init__(self) -> None:
        self.questions: list[str] = []

    async def generate(self, question, chunks, *, system_prompt=None):
        self.questions.append(question)
        return GeneratedAnswer(
            answer='{"heading":"Confidentiality","body":"[INPUT_1] must protect [INPUT_2].",'
            '"rationale":"Protects the stated purpose.","risk_notes":[]}',
            provider="stub",
            model="stub",
        )


@pytest.mark.asyncio
async def test_draft_generation_aliases_inputs_before_provider_call() -> None:
    generator = RecordingGenerator()

    clause = await generate_clause(
        generator,
        template_name="Non-Disclosure Agreement",
        clause_heading="Confidentiality",
        clause_outline=[{"heading": "Confidentiality"}],
        inputs={"disclosing_party": "Acme Legal LLC", "receiving_party": "Jane Roe"},
        prior_clauses=[],
    )

    assert "Acme Legal LLC" not in generator.questions[0]
    assert "Jane Roe" not in generator.questions[0]
    assert clause.body == "Acme Legal LLC must protect Jane Roe."