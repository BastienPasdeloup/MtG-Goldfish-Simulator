"""Worldly Tutor — {G} Instant. Search your library for a creature card,
reveal it, then shuffle and put the card on top (branch)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class WorldlyTutor(Card):
    card_name = "Worldly Tutor"

    def on_resolve(self, state):
        candidates = state.search_library(lambda c: c.is_creature)
        if not candidates:
            return None

        def apply(st, name: str):
            card = next(c for c in st.library if c.name == name)
            st.take_from_library(card)
            st.shuffle_library()
            st.library.insert(0, card)
            st.mark_known_in_library(card)  # player knows it's on top
            st.emit(f"Worldly Tutor: {name} on top — shuffle")

        return branch_over(state, [c.name for c in candidates], apply)
