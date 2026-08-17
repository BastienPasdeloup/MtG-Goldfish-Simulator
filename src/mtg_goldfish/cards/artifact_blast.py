"""Artifact Blast — {R} Instant. Counter target artifact spell.

Like every counterspell in this solitaire engine it needs a spell on the stack;
only reachable under instant-speed exploration (counter your OWN artifact spell)."""
from __future__ import annotations

from ._common import counterspell

ArtifactBlast = counterspell("Artifact Blast", target=lambda c: c.is_artifact)
