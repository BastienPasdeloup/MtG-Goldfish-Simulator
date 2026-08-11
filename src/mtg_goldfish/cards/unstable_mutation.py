"""Unstable Mutation — {U} Enchantment — Aura. Enchant creature.
Enchanted creature gets +3/+3.
At the beginning of the upkeep of enchanted creature's controller, put a -1/-1
counter on that creature.

A big cheap buff that decays: +3/+3 via equip_mod, and each of your upkeeps adds a
-1/-1 counter to the host (so the net bonus shrinks by 1/1 per turn)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class UnstableMutation(Card):
    card_name = "Unstable Mutation"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{U}")

    def equip_mod(self, state, perm):
        return (3, 3)

    def on_phase(self, state, perm, phase):
        host = state.find_permanent(perm.attached_to) if perm.attached_to else None
        if host is not None:
            host.counters["-1/-1"] = host.counters.get("-1/-1", 0) + 1
            state.emit(f"Unstable Mutation: -1/-1 counter on {host.name}")
            state.check_deaths()
        return None
