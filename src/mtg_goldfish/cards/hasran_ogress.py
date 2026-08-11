"""Hasran Ogress — {B}{B} Creature — Ogre 3/2.
Whenever this creature attacks, it deals 3 damage to you unless you pay {2}.

A cheap 3/2 with an attack tax: each time it attacks, a branch — pay {2}, or take 3
damage."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class HasranOgress(Card):
    card_name = "Hasran Ogress"

    def on_attack(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)

        def fn(st, opt):
            if opt == "pay" and can_afford(st, cost) and pay_cost(st, cost):
                st.emit("Hasran Ogress: pay {2} (no damage)")
            else:
                dealt = st.damage_self(3, colors=("B",))
                st.emit(f"Hasran Ogress: {dealt} damage to you (didn't pay)")
            return None

        return branch_over(state, ["take", "pay"], fn)
