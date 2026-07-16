"""Simian Spirit Guide — {2}{R} Creature 2/2.
Exile this card from your hand: Add {R}. (A ritual played from hand.)"""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class SimianSpiritGuide(Card):
    card_name = "Simian Spirit Guide"

    def hand_actions(self, state):
        if not any(c.name == self.card_name for c in state.hand):
            return []

        def fn(st):
            card = next((c for c in st.hand if c.name == self.card_name), None)
            if card is None:
                return None
            st.hand.remove(card)
            st.exile.append(card)
            st.mana_pool.add("R", 1)
            st.emit("Simian Spirit Guide: exile from hand — add {R}")
            return None

        return [CardAction("Simian Spirit Guide: exile → {R}", fn)]
