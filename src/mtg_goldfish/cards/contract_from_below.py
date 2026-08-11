"""Contract from Below — {B} Sorcery.
(Ante card.) Discard your hand, ante the top card of your library, then draw
seven cards.

The ante is modelled as exiling the anted card with an "ante" badge (never won
back in a goldfish); the discard-hand-then-draw-seven is a real hand refill."""
from __future__ import annotations

from ._common import ante_top_card
from .base import Card
from .registry import register


@register
class ContractFromBelow(Card):
    card_name = "Contract from Below"

    def on_resolve(self, state):
        n = len(state.hand)
        for c in list(state.hand):
            state.discard(c)
        ante_top_card(state)
        state.draw(7)
        state.emit(f"Contract from Below: discard {n}, ante the top card, draw 7")
