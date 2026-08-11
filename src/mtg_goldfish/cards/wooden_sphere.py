"""Wooden Sphere — {1} Artifact.
Whenever a player casts a green spell, you may pay {1}. If you do, you gain 1 life.

On each green spell you cast, a branch: pay {1} and gain 1 life, or decline."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class WoodenSphere(Card):
    card_name = "Wooden Sphere"

    def on_cast_other(self, state, perm, card):
        from ..engine.actions import can_afford, pay_cost

        if "G" not in (card.colors or []):
            return None
        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.life += 1
                st.emit("Wooden Sphere: pay {1}, gain 1 life")
            return None

        return branch_over(state, ["decline", "pay"], fn)
