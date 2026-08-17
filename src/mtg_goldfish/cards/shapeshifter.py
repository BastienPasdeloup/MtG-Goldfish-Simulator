"""Shapeshifter — {6} Artifact Creature — Shapeshifter */7-*.
As this creature enters, choose a number between 0 and 7. At the beginning of your
upkeep, you may choose a number between 0 and 7. Its power = the last chosen number
and its toughness = 7 minus that number.

The chosen number is stored in a counter and read by dynamic P/T; both the entry
choice and each upkeep re-choice fan out one branch per value (0..7)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class Shapeshifter(Card):
    card_name = "Shapeshifter"
    trigger_phase = Phase.UPKEEP

    def _choose(self, state, perm, verb):
        def fn(st, n):
            me = st.find_permanent(perm.uid)
            if me is not None:
                me.counters["shape"] = n
                st.emit(f"Shapeshifter {verb} {n}/{7 - n}")
            return None

        return branch_over(state, list(range(8)), fn)

    def enter_choices(self, state, perm):
        return self._choose(state, perm, "enters as")

    def on_phase(self, state, perm, phase):
        return self._choose(state, perm, "becomes")

    def dynamic_power(self, state, perm):
        return perm.counters.get("shape", 0)

    def dynamic_toughness(self, state, perm):
        return 7 - perm.counters.get("shape", 0)
