"""Anthropic-backed LLM provider (uses the official `anthropic` SDK)."""
from __future__ import annotations

from ..config import CONFIG
from .provider import LLMProvider


class AnthropicProvider(LLMProvider):
    is_real = True

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        # Imported lazily so the app can run without the SDK installed/keyed.
        import anthropic

        self._model = model or CONFIG.llm_model
        self._client = anthropic.Anthropic(api_key=api_key or CONFIG.anthropic_api_key)

    @property
    def name(self) -> str:
        return f"anthropic:{self._model}"

    def generate(self, system: str, prompt: str, *, max_tokens: int = 4096) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if block.type == "text"]
        return "".join(parts).strip()
