"""Urza's Cave — Land — Urza's Cave.
{T}: Add {C}. {3}, {T}, Sacrifice: search your library for a land card, put
it onto the battlefield tapped, then shuffle (branch per distinct land)."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
from ._common import enter_battlefield
from .base import Card, CardAction
from .registry import register


@register
class UrzasCave(Card):
    card_name = "Urza's Cave"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        cost = ManaCost(generic=3)
        # Taps for the ability, so it can't help pay its own {3} cost.
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def make(name):
            def pay(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
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
                enter_battlefield(
                    st,
                    card,
                    tapped=True,
                    announce=f"Urza's Cave: fetch {name} tapped — shuffle",
                )
                return None
            return CardAction.activated(
                f"Urza's Cave: fetch {name}",
                pay,
                resolve,
                source_name="Urza's Cave",
                ability_text=f"Fetch {name}",
            )

        return [make(t.name) for t in state.search_library(lambda c: c.is_land)]
