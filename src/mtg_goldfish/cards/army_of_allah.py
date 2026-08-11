"""Army of Allah — {1}{W}{W} Instant.
Attacking creatures get +2/+0 until end of turn.

A one-shot combat pump: every creature currently attacking gets +2/+0 for the
turn."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class ArmyOfAllah(Card):
    card_name = "Army of Allah"

    def on_resolve(self, state):
        n = 0
        for p in state.battlefield:
            if p.is_creature_now and p.uid in state.attackers:
                p.temp_power += 2
                n += 1
        state.emit(f"Army of Allah: {n} attacking creature(s) get +2/+0")
