"""Archdruid's Charm — {G}{G}{G} Instant.
Modal. Only the first mode is useful in a goldfish: search your library for a
creature or land card; put a land onto the battlefield tapped, else put it
into your hand; then shuffle. Branch over the search target. (The fight mode
needs opponent creatures; the exile mode targets your own permanents — both
skipped as documented approximations.)"""
from __future__ import annotations

from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class ArchdruidsCharm(Card):
    card_name = "Archdruid's Charm"

    def cast_actions(self, state):
        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []
        targets = state.search_library(lambda c: c.is_creature or c.is_land)

        def make(name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                if card is None or not begin_cast(st, card, cost):
                    return None
                resolve_to_graveyard(st, card)
                found = next((c for c in st.library if c.name == name), None)
                if found is None:
                    return None
                st.take_from_library(found)
                st.shuffle_library()
                if found.is_land:
                    enter_battlefield(
                        st,
                        found,
                        tapped=True,
                        announce=f"Archdruid's Charm: {name} onto the battlefield tapped — shuffle",
                    )
                    return None
                else:
                    st.hand.append(found)
                    st.emit(f"Archdruid's Charm: {name} to hand — shuffle")
                return None
            return fn

        return [CardAction(f"cast Archdruid's Charm → {t.name}", make(t.name)) for t in targets]
