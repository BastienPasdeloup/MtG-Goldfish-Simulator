"""Khabál Ghoul — {2}{B} Creature — Zombie 1/1.
At the beginning of each end step, put a +1/+1 counter on this creature for each
creature that died this turn.

Grows from the deaths-this-turn tracker: each end step it gains a +1/+1 counter per
creature that died this turn."""
from __future__ import annotations

from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class KhabalGhoul(Card):
    card_name = "Khabál Ghoul"
    trigger_phase = Phase.END_STEP

    def on_phase(self, state, perm, phase):
        n = state.deaths_this_turn
        if n:
            p = state.find_permanent(perm.uid)
            if p is not None:
                p.counters["+1/+1"] = p.counters.get("+1/+1", 0) + n
                state.emit(f"Khabál Ghoul: +{n} +1/+1 counter(s) ({n} creatures died)")
        return None
