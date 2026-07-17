"""Auroral Procession — {G}{U} Instant. Return target card from your graveyard to
your hand (branch per distinct card)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class AuroralProcession(Card):
    card_name = "Auroral Procession"

    def on_resolve(self, state):
        names = sorted({c.name for c in state.graveyard})
        if not names:
            return None

        def fn(st, name):
            c = next((x for x in st.graveyard if x.name == name), None)
            if c is not None:
                st.leave_graveyard(c)
                st.hand.append(c)
                st.emit(f"Auroral Procession: return {name} to hand")
            return None

        return branch_over(state, names, fn)
