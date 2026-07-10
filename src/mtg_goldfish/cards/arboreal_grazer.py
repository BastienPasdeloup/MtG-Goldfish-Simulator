"""Arboreal Grazer — {G} Creature — Sloth Beast 0/3, reach.
ETB: you may put a land card from your hand onto the battlefield tapped
(one branch per distinct land, plus declining)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class ArborealGrazer(Card):
    card_name = "Arboreal Grazer"

    def on_etb(self, state, permanent):
        names = sorted({c.name for c in state.hand if c.is_land})
        if not names:
            return None

        def fn(st, name):
            if name is None:
                return
            card = next((c for c in st.hand if c.name == name), None)
            if card is None:
                return
            st.hand.remove(card)
            st.put_on_battlefield(
                card, tapped=True,
                announce=f"Arboreal Grazer: put {name} onto the battlefield tapped",
            )

        return branch_over(state, names + [None], fn)
