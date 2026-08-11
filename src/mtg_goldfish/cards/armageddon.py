"""Armageddon — {3}{W} Sorcery.
Destroy all lands.

Symmetric — in a solitaire goldfish that means all of YOUR lands (a phantom
opponent has none), so it wipes your mana base. Faithful and rarely good here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Armageddon(Card):
    card_name = "Armageddon"

    def on_resolve(self, state):
        lands = [p for p in state.battlefield if p.is_land]
        for p in lands:
            state.leaves_battlefield(p, "graveyard", reason="destroy")
        state.emit(f"Armageddon: destroy all lands ({len(lands)})")
