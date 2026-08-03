"""Peek — {U} Instant. Look at target player's hand (no effect in a goldfish).
Draw a card."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Peek(Card):
    card_name = "Peek"

    def on_resolve(self, state):
        state.draw(1)
        state.emit(f"Peek: draw a card ({len(state.hand)} in hand)")
        return None
