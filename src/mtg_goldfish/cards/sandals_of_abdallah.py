"""Sandals of Abdallah — {4} Artifact.
{2}, {T}: Target creature gains islandwalk until end of turn. When that creature
dies this turn, destroy this artifact.

Islandwalk (evasion) is inert with no blockers, so the ability grants nothing
material. Left as a bare artifact that still enters (counting as a permanent)."""
from __future__ import annotations
from .base import Card
from .registry import register
@register
class SandalsOfAbdallah(Card):
    card_name = "Sandals of Abdallah"
