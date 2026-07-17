"""Archmage's Charm — {U}{U}{U} Instant. Choose one — counter target spell;
target player draws two cards; or gain control of a mana-value-1-or-less
nonland permanent. Only the "draw two cards" mode is meaningful in a goldfish."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class ArchmagesCharm(Card):
    card_name = "Archmage's Charm"

    def cast_actions(self, state):
        from ..engine.actions import begin_cast, can_afford, resolve_to_graveyard

        cost = self.cast_cost(state)
        if not can_afford(state, cost):
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not begin_cast(st, card, cost):
                return None
            resolve_to_graveyard(st, card)
            st.draw(2)
            st.emit("Archmage's Charm: draw two cards")
            return None

        return [CardAction("cast Archmage's Charm (draw 2)", fn)]
