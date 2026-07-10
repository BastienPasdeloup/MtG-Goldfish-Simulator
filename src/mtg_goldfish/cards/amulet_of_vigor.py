"""Amulet of Vigor — {1} Artifact.
Whenever a permanent you control enters tapped, untap it."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class AmuletOfVigor(Card):
    card_name = "Amulet of Vigor"

    def etb_tapped(self, state):
        # An artifact — it never enters tapped. (Its oracle text contains the
        # phrase "enters tapped" only inside its triggered ability, which the
        # base heuristic would otherwise misread.)
        return False

    def on_other_etb(self, state, perm, entering):
        # Untap the permanent only when it actually entered tapped.
        if entering.tapped:
            entering.tapped = False
            state.emit(f"Amulet of Vigor: untap {entering.name}")
