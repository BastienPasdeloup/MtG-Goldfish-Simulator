"""Farmstead — {W}{W}{W} Enchantment — Aura. Enchant land.
Enchanted land has "At the beginning of your upkeep, you may pay {W}{W}. If you
do, you gain 1 life."

Enchant one of your lands; each of your upkeeps offers a branch: pay {W}{W} and
gain 1 life, or decline."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ..engine.phases import Phase
from ._common import aura_enchant_actions, branch_over
from .base import Card
from .registry import register


@register
class Farmstead(Card):
    card_name = "Farmstead"
    trigger_phase = Phase.UPKEEP

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}{W}{W}",
                                    pred=lambda p: p.is_land)

    def on_phase(self, state, perm, phase):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(pips=(("W", 1), ("W", 1)))
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.life += 1
                st.emit("Farmstead: pay {W}{W}, gain 1 life")
            return None

        return branch_over(state, ["decline", "pay"], fn)
