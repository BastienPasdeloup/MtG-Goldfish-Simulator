"""Demonic Tutor — {1}{B} Sorcery. Search your library for a card, put it into
your hand, then shuffle (branch per distinct card name)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class DemonicTutor(Card):
    card_name = "Demonic Tutor"

    def on_resolve(self, state):
        candidates = state.search_library(lambda c: True)
        if not candidates:
            return None

        def apply(st, name: str):
            card = next(c for c in st.library if c.name == name)
            st.take_from_library(card)
            st.hand.append(card)
            st.shuffle_library()
            st.emit(f"Demonic Tutor: {name} to hand — shuffle")

        return branch_over(state, [c.name for c in candidates], apply)
