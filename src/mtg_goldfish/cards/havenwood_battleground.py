"""Havenwood Battleground — Land.
Enters tapped. {T}: Add {G}. {T}, Sacrifice: add {G}{G} (battlefield action;
the mana goes to the pool, usable this phase)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class HavenwoodBattleground(Card):
    card_name = "Havenwood Battleground"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def fn(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return None
            st.leaves_battlefield(p, "graveyard")
            st.mana_pool.add("G", 2)
            st.emit("Havenwood Battleground: sacrifice — add {G}{G}")
            return None

        return [CardAction("Havenwood Battleground: sacrifice for {G}{G}", fn)]
