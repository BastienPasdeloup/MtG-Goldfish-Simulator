"""Timetwister — {2}{U} Sorcery.
Each player shuffles their hand and graveyard into their library, then draws seven
cards.

For you: your hand and graveyard go into your library, shuffle, then draw seven.
(Timetwister itself is on the stack resolving, so it's already left your hand.)"""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Timetwister(Card):
    card_name = "Timetwister"

    def on_resolve(self, state):
        moved = len(state.hand) + len(state.graveyard)
        state.library.extend(state.hand)
        state.library.extend(state.graveyard)
        state.hand.clear()
        state.graveyard.clear()
        state.shuffle_library()
        state.emit(f"Timetwister: shuffle {moved} cards into library, draw 7")
        state.draw(7)
