"""MtG Goldfish Simulator.

A solitaire Magic: the Gathering simulator. Given a deck and a set of
user-defined properties, it exhaustively explores lines of play and reports
how often the properties can be satisfied.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

#: Major.minor is the release line (set by hand, matches pyproject.toml); the
#: patch is the git commit count, so the user-facing version bumps on every push
#: WITHOUT committing anything back — pyproject.toml / uv.lock never move, and
#: local always equals the server. Falls back to ``.0`` for a non-git install.
__version_base__ = "0.1"


def _commit_count() -> int | None:
    root = Path(__file__).resolve().parents[2]
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    n = out.stdout.strip()
    return int(n) if out.returncode == 0 and n.isdigit() else None


_build = _commit_count()
__version__ = f"{__version_base__}.{_build if _build is not None else 0}"
