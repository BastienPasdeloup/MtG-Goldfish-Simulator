"""Jalum Tome — {3} Artifact — Book.
{2}, {T}: Draw a card, then discard a card.

A loot engine (branches over which card to discard, including the one drawn)."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import loot
from .base import Card, CardAction
from .registry import register


@register
class JalumTome(Card):
    card_name = "Jalum Tome"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if perm.tapped or not can_afford(state, cost, exclude_uids={perm.uid}):
            return []

        def pay(st):
            live = st.find_permanent(perm.uid)
            if live is None or live.tapped or not pay_cost(st, cost, exclude_uids={perm.uid}):
                return False
            live.tapped = True
            return True

        def resolve(st):
            return loot(st, 1, 1, source="Jalum Tome")

        return [CardAction.activated(
            "Jalum Tome: {2}, {T} — draw a card, then discard a card",
            pay, resolve, source_name="Jalum Tome",
            ability_text="Draw a card, then discard a card")]
