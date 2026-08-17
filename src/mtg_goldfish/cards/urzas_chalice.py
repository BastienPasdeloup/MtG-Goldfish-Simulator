"""Urza's Chalice — {1} Artifact.
Whenever a player casts an artifact spell, you may pay {1}. If you do, you gain 1
life.

Fires when YOU cast an artifact spell (the phantom opponent never casts) — a
branch to pay {1} for 1 life or decline."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import branch_over
from .base import Card
from .registry import register


@register
class UrzasChalice(Card):
    card_name = "Urza's Chalice"

    def on_cast_other(self, state, perm, card):
        if not card.is_artifact or getattr(state, "_suppress_responses", False):
            return None
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=1)
        if not can_afford(state, cost):
            return None

        def fn(st, opt):
            if opt == "pay" and pay_cost(st, cost):
                st.gain_life(1)
                st.emit(f"Urza's Chalice: pay {{1}}, gain 1 life ({st.life})")
            return None

        return branch_over(state, ["decline", "pay"], fn)
