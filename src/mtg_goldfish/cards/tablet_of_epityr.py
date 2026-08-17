"""Tablet of Epityr — {1} Artifact.
Whenever an artifact you control is put into a graveyard from the battlefield,
you may pay {1}. If you do, you gain 1 life.

A death watcher over your artifacts (`on_other_leave`, to == graveyard) — a
branch to pay {1} for 1 life or decline."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class TabletOfEpityr(Card):
    card_name = "Tablet of Epityr"

    def on_other_leave(self, state, perm, left, to, reason):
        if to != "graveyard" or not left.is_artifact:
            return None
        if getattr(state, "_suppress_responses", False):
            return None
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.gain_life(1)
                st.emit(f"Tablet of Epityr: pay {{1}}, gain 1 life ({st.life})")
            return None

        return branch_over(state, ["decline", "pay"], fn)
