"""Currency Converter — {1} Artifact.
{2}, {T}: Draw a card, then discard a card (loot).
Approximation: the discard-exile trigger and the {T} "return an exiled card as a
Treasure or 2/2 Rogue" ability are not modelled — the repeatable loot is the
goldfish-relevant part."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import loot
from .base import Card, CardAction
from .registry import register

_COST = ManaCost(generic=2)


@register
class CurrencyConverter(Card):
    card_name = "Currency Converter"

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        if perm.tapped or not can_afford(state, _COST, exclude_uids={perm.uid}):
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or not pay_cost(st, _COST, exclude_uids={p.uid}):
                return False
            p.tapped = True
            return True

        def resolve(st):
            return loot(st, 1, 1, source="Currency Converter")

        return [CardAction.activated(
            "Currency Converter: {2}, {T}: loot", pay, resolve,
            source_name="Currency Converter", ability_text="Draw a card, then discard a card")]
