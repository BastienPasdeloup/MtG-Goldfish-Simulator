"""Expedition Map — {1} Artifact.
{2}, {T}, Sacrifice: search your library for a land card, put it into your
hand, then shuffle (one branch per distinct land)."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class ExpeditionMap(Card):
    card_name = "Expedition Map"

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost):
            return []

        def make(name):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, cost):
                    return False
                st.leaves_battlefield(p, "graveyard")
                return True

            def resolve(st):
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                st.hand.append(card)
                st.emit(f"Expedition Map: search {name} to hand — shuffle")
                return None
            return CardAction.activated(
                f"Expedition Map: search {name}",
                pay,
                resolve,
                source_name="Expedition Map",
                ability_text=f"Search {name} to hand",
            )

        return [make(t.name) for t in state.search_library(lambda c: c.is_land)]
