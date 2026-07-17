"""Mystic Confluence — {3}{U}{U} Instant. Choose three (repeatable) — counter a
spell unless {3} is paid; return a creature to its owner's hand; or draw a card.
In a goldfish the always-useful line is drawing three cards."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class MysticConfluence(Card):
    card_name = "Mystic Confluence"

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
            st.draw(3)
            st.emit("Mystic Confluence: draw three cards")
            return None

        return [CardAction("cast Mystic Confluence (draw 3)", fn)]
