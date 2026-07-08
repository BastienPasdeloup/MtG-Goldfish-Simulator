"""Tithe — {W} Instant. Search your library for a Plains card (the extra
search requires the opponent to control more lands than you — never true in a
solitaire game), reveal it, put it into your hand, then shuffle."""
from __future__ import annotations

from ._common import branch_over, has_subtype
from .base import Card
from .registry import register


@register
class Tithe(Card):
    card_name = "Tithe"

    def on_resolve(self, state):
        candidates = state.search_library(lambda c: c.is_land and has_subtype(c, ("Plains",)))
        if not candidates:
            state.shuffle_library()
            state.emit("Tithe: no Plains found — shuffle")
            return None

        def apply(st, name: str):
            card = next(c for c in st.library if c.name == name)
            st.take_from_library(card)
            st.hand.append(card)
            st.shuffle_library()
            st.emit(f"Tithe: {name} to hand — shuffle")

        return branch_over(state, [c.name for c in candidates], apply)
