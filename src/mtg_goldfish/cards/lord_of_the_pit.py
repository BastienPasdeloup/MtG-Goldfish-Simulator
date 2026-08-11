"""Lord of the Pit — {4}{B}{B}{B} Creature — Demon 7/7. Flying, trample.
At the beginning of your upkeep, sacrifice a creature other than this creature. If
you can't, this creature deals 7 damage to you.

Upkeep tax: you MUST sacrifice another creature if able (one branch per distinct
sacrifice choice); with no other creature it deals you 7 (via damage_self, black
source)."""
from __future__ import annotations

from ..engine.phases import Phase
from ._common import branch_over
from .base import Card
from .registry import register


@register
class LordOfThePit(Card):
    card_name = "Lord of the Pit"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        others = []
        seen: set[str] = set()
        for p in state.battlefield:
            if p.uid == perm.uid or not p.is_creature_now or p.name in seen:
                continue
            seen.add(p.name)
            others.append(p.uid)

        if not others:
            dealt = state.damage_self(7, colors=("B",))
            state.emit(f"Lord of the Pit: no creature to sacrifice — {dealt} damage to you")
            return None

        def fn(st, uid):
            victim = st.find_permanent(uid)
            if victim is not None:
                st.emit(f"Lord of the Pit: sacrifice {victim.name}")
                st.leaves_battlefield(victim, "graveyard", reason="sacrifice")
            return None

        return branch_over(state, others, fn)
