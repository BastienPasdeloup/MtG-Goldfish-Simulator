"""Tsunami — {3}{G} Sorcery. Destroy all Islands.

Symmetric like Flashfires but for Islands — in a solitaire goldfish it destroys
all of YOUR Islands. Respects indestructible."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Tsunami(Card):
    card_name = "Tsunami"

    def on_resolve(self, state):
        islands = [p for p in state.battlefield
                   if p.is_land and "island" in p.type_line.lower()]
        for p in islands:
            state.leaves_battlefield(p, "graveyard", reason="destroy")
        state.emit(f"Tsunami: destroy all Islands ({len(islands)})")
