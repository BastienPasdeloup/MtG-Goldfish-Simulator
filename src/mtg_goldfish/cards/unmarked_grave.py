"""Unmarked Grave — {1}{B} Sorcery. Search your library for a nonlegendary card,
put it into your graveyard, then shuffle (branch per distinct card — a reanimator
enabler that bins a fatty)."""
from __future__ import annotations

from ._common import branch_over
from .base import Card
from .registry import register


@register
class UnmarkedGrave(Card):
    card_name = "Unmarked Grave"

    def on_resolve(self, state):
        cands = state.search_library(
            lambda c: "legendary" not in c.type_line.lower())
        names = sorted({c.name for c in cands})
        if not names:
            return None

        def fn(st, name):
            c = next((x for x in st.library if x.name == name), None)
            if c is not None:
                st.take_from_library(c)
                st.to_graveyard(c)
            st.shuffle_library()
            st.emit(f"Unmarked Grave: {name} to graveyard — shuffle")
            return None

        return branch_over(state, names, fn)
