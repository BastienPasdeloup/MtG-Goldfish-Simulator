"""Library of Alexandria — Land.
{T}: Add {C}.
{T}: Draw a card. Activate only if you have exactly seven cards in hand.

Taps for {C}, or (a different {T}) draws a card while you hold exactly seven — the
famous card-advantage engine."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card, CardAction
from .registry import register


@register
class LibraryOfAlexandria(Card):
    card_name = "Library of Alexandria"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        if perm.tapped or len(state.hand) != 7:
            return []

        def pay(st):
            p = st.find_permanent(perm.uid)
            if p is None or p.tapped or len(st.hand) != 7:
                return False
            p.tapped = True
            return True

        def resolve(st):
            st.draw(1)
            st.emit("Library of Alexandria: draw a card")
            return None

        return [CardAction.activated(
            "Library of Alexandria: {T} — draw a card (hand of exactly 7)",
            pay, resolve, source_name="Library of Alexandria",
            ability_text="Draw a card")]
