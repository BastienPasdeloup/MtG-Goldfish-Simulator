"""Hickory Woodlot — Land.
Enters tapped with two depletion counters (a replacement effect: the counters
are on it from the moment it enters — nothing goes on the stack). {T}, Remove
a depletion counter: add {G}{G}; when none remain, sacrifice it. The counter
removal (and the sacrifice) happens via on_tap_for_mana."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class HickoryWoodlot(Card):
    card_name = "Hickory Woodlot"

    def etb_tapped(self, state):
        return True

    def enters_with_counters(self, state):
        return {"depletion": 2}

    def mana_abilities_perm(self, state, perm):
        if perm.counters.get("depletion", 0) <= 0:
            return []
        return [ManaAbility(amount=2, choices=("G",))]

    def on_tap_for_mana(self, state, permanent, color):
        permanent.counters["depletion"] = permanent.counters.get("depletion", 0) - 1
        if permanent.counters["depletion"] <= 0:
            state.emit("Hickory Woodlot: no depletion counters — sacrifice")
            state.leaves_battlefield(permanent, "graveyard")
