"""LLM provider selection."""
from __future__ import annotations

from ..config import CONFIG
from .provider import LLMProvider
from .stub_provider import StubProvider

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    """Return the active provider: Anthropic if a key is configured, else the
    deterministic stub. Cached for the process."""
    global _provider
    if _provider is not None:
        return _provider
    if CONFIG.has_llm:
        try:
            from .anthropic_provider import AnthropicProvider

            _provider = AnthropicProvider()
        except Exception:
            _provider = StubProvider()
    else:
        _provider = StubProvider()
    return _provider


def set_provider(provider: LLMProvider) -> None:
    """Override the provider (used by tests)."""
    global _provider
    _provider = provider


__all__ = ["LLMProvider", "StubProvider", "get_provider", "set_provider"]
