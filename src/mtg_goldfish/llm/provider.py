"""LLM provider interface.

Everything the app needs from an LLM goes through `LLMProvider.generate`. This
keeps the Anthropic dependency behind one seam so it can be swapped for the
deterministic stub (used when no API key is configured, and in tests).
"""
from __future__ import annotations

import abc


class LLMProvider(abc.ABC):
    """Minimal text-in/text-out interface."""

    #: Whether this provider talks to a real model (vs. the offline stub).
    is_real: bool = True

    @abc.abstractmethod
    def generate(self, system: str, prompt: str, *, max_tokens: int = 4096) -> str:
        """Return the model's text completion for a system + user prompt."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...
