"""Prismatic Vista — Land.
{T}, Pay 1 life, Sacrifice: search your library for a basic land card, put it
onto the battlefield (untapped), then shuffle."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class PrismaticVista(Card):
    card_name = "Prismatic Vista"

    def battlefield_actions(self, state, perm):
        if perm.tapped or state.life <= 1:
            return []
        targets = state.search_library(
            lambda c: c.is_land and "basic" in c.type_line.lower()
        )

        def make(name):
            def fn(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or st.life <= 1:
                    return None
                p.tapped = True
                st.life -= 1
                st.leaves_battlefield(p, "graveyard")
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                st.put_on_battlefield(card)
                st.emit(f"Prismatic Vista: pay 1 life, fetch {name} — shuffle")
                return None
            return fn

        return [CardAction(f"Prismatic Vista: fetch {t.name}", make(t.name)) for t in targets]
