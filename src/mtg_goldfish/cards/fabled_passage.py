"""Fabled Passage — Land.
{T}, Sacrifice: search your library for a basic land card, put it onto the
battlefield tapped, then shuffle. Then if you control four or more lands,
untap that land."""
from __future__ import annotations

from ._common import enter_battlefield
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
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped:
                    return False
                p.tapped = True
                st.leaves_battlefield(p, "graveyard")
                return True

            def resolve(st):
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                lands = sum(1 for q in st.battlefield if "land" in q.type_line.lower())
                tapped = lands + 1 < 4  # counting the fetched land itself
                enter_battlefield(
                    st,
                    card,
                    tapped=tapped,
                    announce=(
                        f"Fabled Passage: fetch {name}"
                        f"{' tapped' if tapped else ' untapped (4+ lands)'} — shuffle"
                    ),
                )
                return None
            return CardAction.activated(
                f"Fabled Passage: fetch {name}",
                pay,
                resolve,
                source_name="Fabled Passage",
                ability_text=f"Fetch {name}",
            )

        return [make(t.name) for t in targets]
