"""Enlightened Tutor — {W} Instant. Search your library for an artifact or
enchantment card, reveal it, then shuffle and put that card on top (branch)."""
from __future__ import annotations

from ._common import branch_over, type_matches
from .base import Card
from .registry import register


@register
class EnlightenedTutor(Card):
    card_name = "Enlightened Tutor"

    def on_resolve(self, state):
        candidates = state.search_library(
            lambda c: type_matches(c, "artifact", "enchantment")
        )
        if not candidates:
            return None

        def apply(st, name: str):
            card = next(c for c in st.library if c.name == name)
            st.take_from_library(card)
            st.shuffle_library()
            st.library.insert(0, card)
            st.emit(f"Enlightened Tutor: {name} on top — shuffle")

        return branch_over(state, [c.name for c in candidates], apply)
