"""Catalog of selectable LLM backends + persisted selection.

The app can be driven by:
  * the offline **stub** (regex; no download, no key) — the default;
  * a **local** open model served by Ollama (https://ollama.com) — private,
    free, downloaded once with `ollama pull <model>`;
  * the **Anthropic API** (needs an API key).

The user's choice is persisted to `data/llm_config.json`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from ..config import CONFIG

_SETTINGS_PATH = CONFIG.data_dir / "llm_config.json"


@dataclass(frozen=True)
class ModelOption:
    id: str                 # stable id, e.g. "ollama:qwen2.5-coder:7b"
    label: str              # human label
    kind: str               # "stub" | "local" | "api"
    size: str = ""          # rough download size for local models
    detail: str = ""        # one-line description / requirement note
    ollama_model: str = ""  # the tag to `ollama pull` / call, for local
    needs_key: bool = False # API models: requires an API key


#: Offered models. Local ones are open weights good at code, spanning sizes so
#: the user can trade quality for disk/RAM. Ordered small → large.
CATALOG: list[ModelOption] = [
    ModelOption(
        id="stub", label="Offline stub (no download)", kind="stub",
        detail="Deterministic regex — property conditions only; can't implement cards.",
    ),
    ModelOption(
        id="ollama:qwen2.5-coder:1.5b", label="Qwen2.5-Coder 1.5B (local)",
        kind="local", size="~1.0 GB", ollama_model="qwen2.5-coder:1.5b",
        detail="Tiny code model — fastest, lowest quality. Runs on most laptops.",
    ),
    ModelOption(
        id="ollama:qwen2.5-coder:7b", label="Qwen2.5-Coder 7B (local)",
        kind="local", size="~4.7 GB", ollama_model="qwen2.5-coder:7b",
        detail="Balanced local code model. ~8 GB RAM recommended.",
    ),
    ModelOption(
        id="ollama:llama3.1:8b", label="Llama 3.1 8B (local)",
        kind="local", size="~4.9 GB", ollama_model="llama3.1:8b",
        detail="General-purpose local model. ~8 GB RAM recommended.",
    ),
    ModelOption(
        id="ollama:qwen2.5-coder:32b", label="Qwen2.5-Coder 32B (local)",
        kind="local", size="~20 GB", ollama_model="qwen2.5-coder:32b",
        detail="Large local code model — best local quality. Needs a strong GPU / 32 GB+ RAM.",
    ),
    ModelOption(
        id="anthropic:claude-opus-4-8", label="Claude Opus 4.8 (Anthropic API)",
        kind="api", needs_key=True, ollama_model="",
        detail="Highest quality. Requires an ANTHROPIC_API_KEY (sent to Anthropic).",
    ),
]

CATALOG_BY_ID = {m.id: m for m in CATALOG}


def load_selection() -> str:
    """Return the selected model id (defaults to the stub)."""
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
        mid = data.get("model_id")
        if mid in CATALOG_BY_ID:
            return mid
    except Exception:
        pass
    # Auto-prefer Anthropic if a key is already configured in the environment.
    if CONFIG.has_llm:
        return "anthropic:claude-opus-4-8"
    return "stub"


def save_selection(model_id: str, api_key: str | None = None) -> None:
    data = {}
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
    except Exception:
        data = {}
    data["model_id"] = model_id
    if api_key:
        data["anthropic_api_key"] = api_key
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2))


def stored_api_key() -> str | None:
    """API key from the settings file, falling back to the environment."""
    try:
        data = json.loads(_SETTINGS_PATH.read_text())
        if data.get("anthropic_api_key"):
            return data["anthropic_api_key"]
    except Exception:
        pass
    return CONFIG.anthropic_api_key


def option_dicts() -> list[dict]:
    return [asdict(m) for m in CATALOG]
