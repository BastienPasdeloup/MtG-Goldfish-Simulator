"""Urza's Miter — {3} Artifact.
Whenever an artifact you control is put into a graveyard from the battlefield, if
it wasn't sacrificed, you may pay {3}. If you do, draw a card.

A death watcher over your artifacts (`on_other_leave`, to == graveyard, reason is
not "sacrifice") — a branch to pay {3} to draw or decline."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class UrzasMiter(Card):
    card_name = "Urza's Miter"

    def on_other_leave(self, state, perm, left, to, reason):
        if to != "graveyard" or not left.is_artifact or reason == "sacrifice":
            return None
        if getattr(state, "_suppress_responses", False):
            return None
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=3)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.draw(1)
                st.emit("Urza's Miter: pay {3}, draw a card")
            return None

        return branch_over(state, ["decline", "pay"], fn)
