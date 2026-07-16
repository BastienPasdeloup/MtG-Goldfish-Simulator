"""Juri, Master of the Revue — {B}{R} Legendary Creature 1/1.
Whenever you sacrifice a permanent, put a +1/+1 counter on Juri.
When Juri dies, it deals damage equal to its power to any target."""
from __future__ import annotations

from ._common import branch_over, damage_any_target_options
from .base import Card
from .registry import register


@register
class JuriMasterOfTheRevue(Card):
    card_name = "Juri, Master of the Revue"

    def on_other_leave(self, state, perm, left, to, reason):
        if reason == "sacrifice":
            perm.counters["+1/+1"] = perm.counters.get("+1/+1", 0) + 1
            state.emit(f"Juri: +1/+1 counter "
                       f"({state.effective_power(perm)}/{state.effective_toughness(perm)})")

    def on_leave(self, state, permanent):
        power = max(0, permanent.base_power() + permanent.counters.get("+1/+1", 0)
                    + permanent.temp_power)
        if power <= 0:
            return None
        options = damage_any_target_options(state)

        def fn(st, opt):
            suffix, apply = opt
            apply(st, power)
            st.emit(f"Juri dies: {power} damage to {suffix}")
            return None

        return branch_over(state, options, fn)
