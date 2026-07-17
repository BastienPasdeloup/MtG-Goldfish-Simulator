"""Shadow of Doubt — {U/B}{U/B} Instant. Players can't search libraries this
turn; draw a card. The search-hate is symmetric and irrelevant in a goldfish;
only the cantrip (draw a card) is modelled."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class ShadowOfDoubt(Card):
    card_name = "Shadow of Doubt"

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
            st.draw(1)
            st.emit("Shadow of Doubt: draw a card")
            return None

        return [CardAction("cast Shadow of Doubt (draw 1)", fn)]
