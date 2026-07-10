"""LLM provider selection.

The active provider follows the user's choice in `catalog` (persisted to
`data/llm_config.json`): the offline stub, a local Ollama model, or the
Anthropic API. Tests can still override via `set_provider`.
"""
from __future__ import annotations

from .catalog import CATALOG_BY_ID, load_selection, stored_api_key
from .provider import LLMProvider
from .stub_provider import StubProvider

_provider: LLMProvider | None = None
_provider_key: str | None = None  # the model id the cached provider was built for


def get_provider() -> LLMProvider:
    """Return the active provider for the current selection, cached until the
    selection changes."""
    global _provider, _provider_key
    model_id = load_selection()
    if _provider is not None and _provider_key == model_id:
        return _provider
    _provider_key = model_id
    _provider = _build(model_id)
    return _provider


def _build(model_id: str) -> LLMProvider:
    option = CATALOG_BY_ID.get(model_id)
    if option is None or option.kind == "stub":
        return StubProvider()
    if option.kind == "local":
        try:
            from .ollama_provider import OllamaProvider

            return OllamaProvider(option.ollama_model)
        except Exception:
            return StubProvider()
    if option.kind == "api":
        try:
            from .anthropic_provider import AnthropicProvider

            model = model_id.split(":", 1)[1]
            return AnthropicProvider(api_key=stored_api_key(), model=model)
        except Exception:
            return StubProvider()
    return StubProvider()


def reset_provider() -> None:
    """Drop the cached provider so the next call rebuilds from the selection."""
    global _provider, _provider_key
    _provider = None
    _provider_key = None


def set_provider(provider: LLMProvider) -> None:
    """Override the provider (used by tests)."""
    global _provider, _provider_key
    _provider = provider
    _provider_key = "<override>"


__all__ = [
    "LLMProvider", "StubProvider",
    "get_provider", "set_provider", "reset_provider",
]
