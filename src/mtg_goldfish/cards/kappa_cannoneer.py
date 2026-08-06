"""Kappa Cannoneer — {5}{U} Artifact Creature — Turtle Warrior 4/4.
Improvise (own keyword). Ward {4} (no effect with no opponent to target it).
Whenever this creature or another artifact you control enters, put a +1/+1
counter on this creature. It can't be blocked this turn.

The "can't be blocked this turn" clause is irrelevant in a solitaire goldfish
(no blockers); the growth is the modelled part. The engine adds the +1/+1
counters to its P/T automatically."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class KappaCannoneer(Card):
    card_name = "Kappa Cannoneer"

    def on_etb(self, state, permanent):
        # Its own entry counts as "this creature ... enters".
        permanent.counters["+1/+1"] = permanent.counters.get("+1/+1", 0) + 1
        state.emit("Kappa Cannoneer: +1/+1 counter (entered)")

    def on_other_etb(self, state, perm, entering):
        if entering.is_artifact:
            perm.counters["+1/+1"] = perm.counters.get("+1/+1", 0) + 1
            state.emit(f"Kappa Cannoneer: +1/+1 counter ({entering.name} entered)")
