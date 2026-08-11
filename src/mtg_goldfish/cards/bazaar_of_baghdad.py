"""Bazaar of Baghdad — Land.
{T}: Draw two cards, then discard three cards.

A card-filtering land (net −1 card, fills the graveyard): {T} to draw two then
discard three (one branch per discard choice)."""
from __future__ import annotations

from ._common import loot
from .base import Card, CardAction
from .registry import register


@register
class BazaarOfBaghdad(Card):
    card_name = "Bazaar of Baghdad"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped:
                return False
            p.tapped = True
            return True

        def resolve(st):
            return st.settle(loot(st, 2, 3, source="Bazaar of Baghdad"))

        return [CardAction.activated(
            "Bazaar of Baghdad: {T} — draw two, discard three",
            pay, resolve, source_name="Bazaar of Baghdad",
            ability_text="Draw two cards, then discard three cards")]
