"""Tests for provider-agnostic answer generation."""

from uuid import UUID

import httpx
import pytest

from backend.app.config import Settings
from backend.app.core.generation import LLMGenerator, build_prompt
from backend.app.core.retrieval import RetrievedChunk

CHUNK = RetrievedChunk(
    chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
    document_id=UUID("10000000-0000-0000-0000-000000000001"),
    chunk_index=0,
    text="Either party may terminate with thirty days notice.",
)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_prompt_numbers_context_for_citations() -> None:
    prompt = build_prompt("When can we terminate?", [CHUNK])

    assert "[1] Either party may terminate" in prompt
    assert "Question: When can we terminate?" in prompt


@pytest.mark.asyncio
async def test_openai_compatible_provider_returns_answer() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Thirty days [1]."}}]}
        )

    settings = Settings(llm_provider="groq", llm_api_key="test-key")
    async with _client(handler) as client:
        result = await LLMGenerator(settings, client).generate("When?", [CHUNK])

    assert result.answer == "Thirty days [1]."
    assert result.provider == "groq"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_anthropic_provider_uses_messages_api() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "Thirty days [1]."}]}
        )

    settings = Settings(llm_provider="anthropic", llm_api_key="test-key")
    async with _client(handler) as client:
        result = await LLMGenerator(settings, client).generate("When?", [CHUNK])

    assert result.answer == "Thirty days [1]."
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["api_key"] == "test-key"


@pytest.mark.asyncio
async def test_ollama_provider_requires_no_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Local answer [1]."}}]}
        )

    settings = Settings(llm_provider="ollama", llm_model="llama3")
    async with _client(handler) as client:
        result = await LLMGenerator(settings, client).generate("When?", [CHUNK])

    assert result.answer == "Local answer [1]."


@pytest.mark.asyncio
async def test_missing_api_key_is_rejected_before_any_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("No provider request should be attempted")

    settings = Settings(llm_provider="openai", llm_api_key=None)
    async with _client(handler) as client:
        with pytest.raises(ValueError, match="API key is required"):
            await LLMGenerator(settings, client).generate("When?", [CHUNK])


@pytest.mark.asyncio
async def test_unsupported_provider_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("No provider request should be attempted")

    settings = Settings(llm_provider="mystery", llm_api_key="test-key")
    async with _client(handler) as client:
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            await LLMGenerator(settings, client).generate("When?", [CHUNK])
