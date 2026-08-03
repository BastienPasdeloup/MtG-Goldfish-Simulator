"""Svyelunite Temple — Land. Enters tapped. {T}: Add {U}.
{T}, Sacrifice this land: Add {U}{U}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class SvyeluniteTemple(Card):
    card_name = "Svyelunite Temple"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            st.leaves_battlefield(p, "graveyard")
            return True

        def resolve(st):
            st.mana_pool.add("U", 2)
            st.emit("Svyelunite Temple: sacrifice — add {U}{U}")
            return None

        return [CardAction.activated(
            "Svyelunite Temple: sacrifice for {U}{U}", pay, resolve,
            source_name="Svyelunite Temple", ability_text="Add {U}{U}")]
