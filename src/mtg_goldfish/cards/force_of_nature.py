"""Force of Nature — {2}{G}{G}{G}{G} Creature — Elemental 8/8. Trample.
At the beginning of your upkeep, this creature deals 8 damage to you unless you
pay {G}{G}{G}{G}.

An 8/8 trampler with an upkeep tax: pay {G}{G}{G}{G} or take 8 (via damage_self,
so any prevention/shields apply). Trample is printed (inert with no blockers)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from .base import Card
from .registry import register


@register
class ForceOfNature(Card):
    card_name = "Force of Nature"
    trigger_phase = Phase.UPKEEP

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("G", 1), ("G", 1), ("G", 1), ("G", 1)))
        if can_afford(state, cost) and pay_cost(state, cost):
            state.emit("Force of Nature: pay {G}{G}{G}{G} (no damage)")
            return None
        dealt = state.damage_self(8, colors=("G",))
        state.emit(f"Force of Nature: {dealt} damage to you (didn't pay)")
        return None
