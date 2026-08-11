"""Junún Efreet — {1}{B}{B} Creature — Efreet 3/3. Flying.
At the beginning of your upkeep, sacrifice this creature unless you pay {B}{B}.

A 3/3 flyer with an upkeep tax: pay {B}{B} to keep it, else sacrifice."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class JununEfreet(Card):
    card_name = "Junún Efreet"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost
        cost = ManaCost(pips=(("B", 1), ("B", 1)))
        if can_afford(state, cost) and pay_cost(state, cost):
            state.emit("Junún Efreet: pay {B}{B} (kept)")
            return None
        p = state.find_permanent(perm.uid)
        if p is not None:
            state.emit("Junún Efreet: didn't pay — sacrifice")
            state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None
