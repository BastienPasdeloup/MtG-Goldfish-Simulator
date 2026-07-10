"""Aftermath Analyst — {1}{G} Creature — Elf Detective 1/3.
ETB: mill three cards. {3}{G}, Sacrifice: return all land cards from your
graveyard to the battlefield tapped."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class AftermathAnalyst(Card):
    card_name = "Aftermath Analyst"

    def on_etb(self, state, permanent):
        state.mill(3)

    def battlefield_actions(self, state, perm):
        cost = ManaCost.parse("{3}{G}")
        if not can_afford(state, cost):
            return []

        def fn(st):
            p = st.find_permanent(perm.uid)
            if p is None or not pay_cost(st, cost):
                return None
            st.leaves_battlefield(p, "graveyard")
            lands = [c for c in st.graveyard if c.is_land]
            for card in lands:
                st.graveyard.remove(card)
                st.put_on_battlefield(card, tapped=True)
            st.emit(f"Aftermath Analyst: sacrifice — return {len(lands)} land(s) tapped")
            return None

        return [CardAction("Aftermath Analyst: {3}{G}, sac — lands from graveyard", fn)]
