"""Wheel of Fortune — {2}{R} Sorcery.
Each player discards their hand, then draws seven cards.

For you: discard your remaining hand to the graveyard, then draw seven. (Wheel of
Fortune itself is already on the stack resolving.)"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class WheelOfFortune(Card):
    card_name = "Wheel of Fortune"

    def on_resolve(self, state):
        n = len(state.hand)
        state.graveyard.extend(state.hand)
        state.hand.clear()
        state.emit(f"Wheel of Fortune: discard {n}, draw 7")
        state.draw(7)
