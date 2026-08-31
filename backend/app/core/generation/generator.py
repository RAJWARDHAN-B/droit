"""Provider-agnostic answer generation over retrieved legal context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from ...config import Settings
from ..retrieval import RetrievedChunk

SYSTEM_PROMPT = (
    "You are Droit, a legal document assistant. "
    "Answer only from the numbered context passages and cite them as [1], [2]. "
    "State plainly when the context does not contain the answer. "
    "Bracketed placeholders such as [EMAIL_1] are redacted personal data; "
    "reproduce them verbatim and never invent the underlying value."
)

_DEFAULT_BASE_URLS = {
    "anthropic": "https://api.anthropic.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
}
_KEYLESS_PROVIDERS = frozenset({"ollama"})
_ANTHROPIC_VERSION = "2023-06-01"


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    provider: str
    model: str


class AnswerGenerator(Protocol):
    async def generate(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> GeneratedAnswer: ...


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Compose a citation-numbered prompt from ranked context passages."""
    context = "\n\n".join(
        f"[{position}] {chunk.text}" for position, chunk in enumerate(chunks, start=1)
    )
    return f"Context:\n{context}\n\nQuestion: {question}"


class LLMGenerator:
    """Calls OpenAI-compatible or Anthropic chat APIs using app-level settings."""

    def __init__(
        self, settings: Settings, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings
        self._client = client

    async def generate(
        self, question: str, chunks: list[RetrievedChunk]
    ) -> GeneratedAnswer:
        if not chunks:
            raise ValueError("Cannot generate an answer without retrieved context")

        provider = self._settings.llm_provider.strip().lower()
        if provider not in _DEFAULT_BASE_URLS:
            supported = ", ".join(sorted(_DEFAULT_BASE_URLS))
            raise ValueError(
                f"Unsupported LLM provider '{provider}'. Supported providers: {supported}"
            )

        api_key = (
            self._settings.llm_api_key.get_secret_value().strip()
            if self._settings.llm_api_key is not None
            else ""
        )
        if provider not in _KEYLESS_PROVIDERS and not api_key:
            raise ValueError(f"An API key is required for the '{provider}' provider")

        base_url = (
            self._settings.llm_base_url or _DEFAULT_BASE_URLS[provider]
        ).rstrip("/")
        prompt = build_prompt(question, chunks)
        if provider == "anthropic":
            url, headers, payload = self._anthropic_request(base_url, api_key, prompt)
        else:
            url, headers, payload = self._openai_request(base_url, api_key, prompt)

        data = await self._post(url, headers, payload)
        return GeneratedAnswer(
            answer=self._extract_answer(provider, data),
            provider=provider,
            model=self._settings.llm_model,
        )

    def _openai_request(
        self, base_url: str, api_key: str, prompt: str
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": self._settings.llm_model,
            "max_tokens": self._settings.llm_max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        return f"{base_url}/chat/completions", headers, payload

    def _anthropic_request(
        self, base_url: str, api_key: str, prompt: str
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }
        payload = {
            "model": self._settings.llm_model,
            "max_tokens": self._settings.llm_max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }
        return f"{base_url}/messages", headers, payload

    async def _post(
        self, url: str, headers: dict[str, str], payload: dict[str, Any]
    ) -> dict[str, Any]:
        if self._client is not None:
            response = await self._client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        async with httpx.AsyncClient(
            timeout=self._settings.llm_timeout_seconds
        ) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    def _extract_answer(self, provider: str, data: dict[str, Any]) -> str:
        if provider == "anthropic":
            blocks = data.get("content") or []
            text = "".join(
                block.get("text", "")
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            )
        else:
            choices = data.get("choices") or []
            first = choices[0] if choices else {}
            text = (first.get("message") or {}).get("content") or ""

        answer = text.strip()
        if not answer:
            raise ValueError("The language model returned an empty response")
        return answer
