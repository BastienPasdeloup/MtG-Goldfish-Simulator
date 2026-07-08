"""Meticulous Archive — Land — Plains Island. Enters tapped.
When it enters, surveil 1 (branch: keep the top card, or put it in the graveyard).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import branch_over
from .base import Card
from .registry import register


@register
class MeticulousArchive(Card):
    card_name = "Meticulous Archive"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("W", "U"))]

    def etb_tapped(self, state):
        return True

    def on_etb(self, state, permanent):
        if not state.library:
            return None

        def apply(st, to_gy: bool):
            if to_gy:
                card = st.library.pop(0)
                st.to_graveyard(card)
                st.emit(f"surveil 1: {card.name} to graveyard")
            else:
                st.emit("surveil 1: keep top card")

        return branch_over(state, [False, True], apply)
