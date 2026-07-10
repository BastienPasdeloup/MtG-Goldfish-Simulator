"""Local LLM provider backed by Ollama (https://ollama.com).

Ollama serves open models on http://localhost:11434 with no API key. Install
it, `ollama pull <model>`, and the model runs entirely on your machine.
"""
from __future__ import annotations

import httpx

from .provider import LLMProvider

OLLAMA_HOST = "http://localhost:11434"


def ollama_available() -> bool:
    try:
        httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=1.5).raise_for_status()
        return True
    except Exception:
        return False


def installed_models() -> set[str]:
    """Model tags currently pulled locally."""
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=2.0)
        r.raise_for_status()
        return {m["name"] for m in r.json().get("models", [])}
    except Exception:
        return set()


class OllamaProvider(LLMProvider):
    is_real = True

    def __init__(self, model: str) -> None:
        self._model = model

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    def generate(self, system: str, prompt: str, *, max_tokens: int = 4096) -> str:
        resp = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": self._model,
                "system": system,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.2},
            },
            timeout=600.0,  # local generation can be slow on big models
        )
        resp.raise_for_status()
        return (resp.json().get("message", {}).get("content") or "").strip()
