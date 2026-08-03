"""Ebon Stronghold — Land. Enters tapped. {T}: Add {B}.
{T}, Sacrifice this land: Add {B}{B}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class EbonStronghold(Card):
    card_name = "Ebon Stronghold"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]

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
            st.mana_pool.add("B", 2)
            st.emit("Ebon Stronghold: sacrifice — add {B}{B}")
            return None

        return [CardAction.activated(
            "Ebon Stronghold: sacrifice for {B}{B}", pay, resolve,
            source_name="Ebon Stronghold", ability_text="Add {B}{B}")]
