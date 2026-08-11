"""Fungusaur — {3}{G} Creature — Fungus Dinosaur 2/2.
Whenever this creature is dealt damage, put a +1/+1 counter on it.

The damage trigger (via on_dealt_damage) fires BEFORE state-based checks, so a
Fungusaur dealt N < lethal damage grows and can survive: 2/2 dealt 2 → +1/+1 →
3/3 with 2 marked damage, survives. Uses the generalized +1/+1 counter."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Fungusaur(Card):
    card_name = "Fungusaur"

    def on_dealt_damage(self, state, perm, amount):
        p = state.find_permanent(perm.uid)
        if p is not None:
            p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + 1
            state.emit("Fungusaur: +1/+1 counter (dealt damage)")
        return None
