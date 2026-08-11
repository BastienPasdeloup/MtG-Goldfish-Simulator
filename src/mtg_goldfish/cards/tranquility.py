"""Tranquility — {2}{G} Sorcery. Destroy all enchantments.

Symmetric — in a solitaire goldfish it destroys YOUR enchantments (including auras
you control). Respects indestructible."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Tranquility(Card):
    card_name = "Tranquility"

    def on_resolve(self, state):
        ench = [p for p in state.battlefield if "enchantment" in p.type_line.lower()]
        for p in ench:
            state.leaves_battlefield(p, "graveyard", reason="destroy")
        state.emit(f"Tranquility: destroy all enchantments ({len(ench)})")
