"""Soul Net — {1} Artifact.
Whenever a creature dies, you may pay {1}. If you do, you gain 1 life.

On each creature death, a branch: pay {1} and gain 1 life, or decline. Fires via
the death watcher (on_other_leave), which resolves as a normal branchable
triggered ability."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class SoulNet(Card):
    card_name = "Soul Net"

    def on_other_leave(self, state, perm, left, to, reason):
        from ..engine.actions import can_afford, pay_cost

        if not (left.is_creature_now and to == "graveyard"):
            return None
        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.gain_life(1)
                st.emit("Soul Net: pay {1}, gain 1 life")
            return None

        return branch_over(state, ["decline", "pay"], fn)
