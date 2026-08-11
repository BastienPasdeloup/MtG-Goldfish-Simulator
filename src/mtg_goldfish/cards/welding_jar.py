"""Welding Jar — {0} Artifact.
Sacrifice this artifact: Regenerate target artifact.

Regeneration only matters against destruction, of which there is none in a
solitaire goldfish, so it has no effect here — a free artifact that counts for
affinity / Emry / improvise (and is sacrifice fodder for Sai, etc.)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WeldingJar(Card):
    card_name = "Welding Jar"
