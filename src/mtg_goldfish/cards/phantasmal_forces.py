"""Phantasmal Forces — {3}{U} Creature — Illusion 4/1. Flying.
At the beginning of your upkeep, sacrifice this creature unless you pay {U}.

An aggressive 4/1 flyer with an upkeep tax: pay {U} to keep it, else sacrifice."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class PhantasmalForces(Card):
    card_name = "Phantasmal Forces"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("U", 1),))
        if can_afford(state, cost) and pay_cost(state, cost):
            state.emit("Phantasmal Forces: pay {U} (kept)")
            return None
        p = state.find_permanent(perm.uid)
        if p is not None:
            state.emit("Phantasmal Forces: didn't pay {U} — sacrifice")
            state.leaves_battlefield(p, "graveyard", reason="sacrifice")
        return None
