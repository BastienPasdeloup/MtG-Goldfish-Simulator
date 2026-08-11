"""Wrath of God — {2}{W}{W} Sorcery. Destroy all creatures. They can't be
regenerated.

Symmetric board wipe — in a solitaire goldfish it destroys YOUR creatures. Any
regeneration shields are removed first ("can't be regenerated"); indestructible
still survives."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WrathOfGod(Card):
    card_name = "Wrath of God"

    def on_resolve(self, state):
        creatures = [p for p in state.battlefield if p.is_creature_now]
        for p in creatures:
            p.counters.pop("regen_shield", None)  # can't be regenerated
            state.leaves_battlefield(p, "graveyard", reason="destroy")
        state.emit(f"Wrath of God: destroy all creatures ({len(creatures)})")
