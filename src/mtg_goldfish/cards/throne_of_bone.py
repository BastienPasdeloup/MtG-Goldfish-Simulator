"""Throne of Bone — {1} Artifact.
Whenever a player casts a black spell, you may pay {1}. If you do, you gain 1 life.

On each black spell you cast, a branch: pay {1} and gain 1 life, or decline."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class ThroneOfBone(Card):
    card_name = "Throne of Bone"

    def on_cast_other(self, state, perm, card):
        from ..engine.actions import can_afford, pay_cost

        if "B" not in (card.colors or []):
            return None
        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.life += 1
                st.emit("Throne of Bone: pay {1}, gain 1 life")
            return None

        return branch_over(state, ["decline", "pay"], fn)
