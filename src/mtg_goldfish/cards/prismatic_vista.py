"""Prismatic Vista — Land.
{T}, Pay 1 life, Sacrifice: search your library for a basic land card, put it
onto the battlefield (untapped), then shuffle."""
from __future__ import annotations

from ._common import enter_battlefield
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
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or st.life <= 1:
                    return False
                p.tapped = True
                st.life -= 1
                st.leaves_battlefield(p, "graveyard")
                return True

            def resolve(st):
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                enter_battlefield(
                    st,
                    card,
                    announce=f"Prismatic Vista: pay 1 life, fetch {name} — shuffle",
                )
                return None
            return CardAction.activated(
                f"Prismatic Vista: fetch {name}",
                pay,
                resolve,
                source_name="Prismatic Vista",
                ability_text=f"Fetch {name}",
            )

        return [make(t.name) for t in targets]
