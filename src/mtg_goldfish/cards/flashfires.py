"""Flashfires — {3}{R} Sorcery.
Destroy all Plains.

Symmetric like Armageddon, but only Plains — in a solitaire goldfish that means
all of YOUR Plains (a phantom opponent has none). Faithful; respects
indestructible."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Flashfires(Card):
    card_name = "Flashfires"

    def on_resolve(self, state):
        plains = [p for p in state.battlefield
                  if p.is_land and "plains" in p.type_line.lower()]
        for p in plains:
            state.leaves_battlefield(p, "graveyard", reason="destroy")
        state.emit(f"Flashfires: destroy all Plains ({len(plains)})")
