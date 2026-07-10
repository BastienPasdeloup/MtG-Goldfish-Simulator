"""Crop Rotation — {G} Instant.
Additional cost: sacrifice a land. Search your library for a land card, put it
onto the battlefield, then shuffle (branch per distinct land). Approximation:
the land sacrificed is chosen deterministically (a tapped land if any, else a
basic, else the first) so only the search target branches."""
from __future__ import annotations

from ._common import enter_battlefield
from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard
from .base import Card, CardAction
from .registry import register


def _sac_pick(state):
    lands = [p for p in state.battlefield if "land" in p.type_line.lower()]
    tapped = [p for p in lands if p.tapped]
    basics = [p for p in lands if "basic" in p.type_line.lower()]
    return (tapped or basics or lands or [None])[0]


@register
class CropRotation(Card):
    card_name = "Crop Rotation"

    def cast_actions(self, state):
        cost = self.cast_cost(state)
        if _sac_pick(state) is None or not can_afford(state, cost):
            return []
        targets = state.search_library(lambda c: c.is_land)

        def make(name):
            def fn(st):
                card = next((c for c in st.hand if c.name == self.card_name), None)
                sac = _sac_pick(st)
                if card is None or sac is None or not begin_cast(st, card, cost):
                    return None
                st.emit(f"Crop Rotation: sacrifice {sac.name}")
                st.leaves_battlefield(sac, "graveyard")
                resolve_to_graveyard(st, card)
                land = next((c for c in st.library if c.name == name), None)
                if land is None:
                    return None
                st.take_from_library(land)
                st.shuffle_library()
                enter_battlefield(
                    st,
                    land,
                    announce=f"Crop Rotation: {name} onto the battlefield — shuffle",
                )
                return None
            return fn

        return [CardAction(f"cast Crop Rotation → {t.name}", make(t.name)) for t in targets]
