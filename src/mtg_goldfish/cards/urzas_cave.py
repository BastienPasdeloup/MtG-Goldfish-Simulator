"""Urza's Cave — Land — Urza's Cave.
{T}: Add {C}. {3}, {T}, Sacrifice: search your library for a land card, put
it onto the battlefield tapped, then shuffle (branch per distinct land)."""
from __future__ import annotations

from ..engine.actions import can_afford, pay_cost
from ..engine.mana import ManaAbility, ManaCost
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
            def fn(st):
                p = st.find_permanent(perm.uid)
                if p is None or p.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                    return None
                p.tapped = True
                st.leaves_battlefield(p, "graveyard")
                card = next((c for c in st.library if c.name == name), None)
                if card is None:
                    return None
                st.take_from_library(card)
                st.shuffle_library()
                st.put_on_battlefield(card, tapped=True)
                st.emit(f"Urza's Cave: fetch {name} tapped — shuffle")
                return None
            return fn

        return [CardAction(f"Urza's Cave: fetch {t.name}", make(t.name))
                for t in state.search_library(lambda c: c.is_land)]
