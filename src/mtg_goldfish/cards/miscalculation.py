"""Miscalculation — {1}{U} Instant. Counter target spell unless its controller
pays {2}. Cycling {2}. The counter is dead in a goldfish (no opponent spell on
the stack), so only the cycling matters here."""
from __future__ import annotations

from ..engine.mana import ManaCost
from .base import Card, CardAction
from .registry import register


@register
class Miscalculation(Card):
    card_name = "Miscalculation"

    def is_castable(self, state):
        return False  # counters a spell on the stack — never present in a goldfish

    def hand_actions(self, state):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        def pay(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None or not pay_cost(st, cost):
                return False
            st.discard(card)
            return True

        def resolve(st):
            st.draw(1)
            st.emit("Miscalculation: cycling — draw a card")
            return None

        return [CardAction.activated("Miscalculation: cycling {2}", pay, resolve,
                                     source_name="Miscalculation", ability_text="Cycling")]
