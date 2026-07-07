"""Central configuration, read from environment (optionally a .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional; the app runs fine without python-dotenv
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a convenience only
    pass


def _project_root() -> Path:
    # src/mtg_goldfish/config.py -> project root is three parents up.
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str | None
    llm_model: str
    data_dir: Path
    scryfall_cache_dir: Path

    @property
    def has_llm(self) -> bool:
        return bool(self.anthropic_api_key)


def load_config() -> Config:
    data_dir = Path(os.environ.get("MTG_DATA_DIR", _project_root() / "data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = data_dir / "scryfall_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return Config(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        llm_model=os.environ.get("MTG_LLM_MODEL", "claude-sonnet-5"),
        data_dir=data_dir,
        scryfall_cache_dir=cache_dir,
    )


CONFIG = load_config()
