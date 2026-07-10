"""Fabled Passage — Land.
{T}, Sacrifice: search your library for a basic land card, put it onto the
battlefield tapped, then shuffle. Then if you control four or more lands,
untap that land."""
from __future__ import annotations

from ._common import branch_over
from .base import Card, CardAction
from .registry import register


@register
class FabledPassage(Card):
    card_name = "Fabled Passage"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        targets = state.search_library(
            lambda c: c.is_land and "basic" in c.type_line.lower()
        )

        def make(name):
            def fn(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped:
                    return None
                p.tapped = True
                st.leaves_battlefield(p, "graveyard")
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                lands = sum(1 for q in st.battlefield if "land" in q.type_line.lower())
                tapped = lands + 1 < 4  # counting the fetched land itself
                st.put_on_battlefield(card, tapped=tapped)
                st.emit(f"Fabled Passage: fetch {name}{' tapped' if tapped else ' untapped (4+ lands)'} — shuffle")
                return None
            return fn

        return [CardAction(f"Fabled Passage: fetch {t.name}", make(t.name)) for t in targets]
