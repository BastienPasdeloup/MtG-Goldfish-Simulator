"""Cremate — {B} Instant. Exile target card from a graveyard, then draw a card
(you may exile a card from your own graveyard — Cremate itself is a legal
target)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class Cremate(Card):
    card_name = "Cremate"

    def on_resolve(self, state):
        names = sorted({c.name for c in state.graveyard})
        if not names:
            state.draw(1)
            return None

        def fn(st, name):
            c = next((x for x in st.graveyard if x.name == name), None)
            if c is not None:
                st.leave_graveyard(c)
                st.exile.append(c)
                st.emit(f"Cremate: exile {name}")
            st.draw(1)
            return None

        return branch_over(state, names, fn)
