"""Mental Note — {U} Instant. Mill two cards, then draw a card."""
from .base import Card
from .registry import register


@register
class MentalNote(Card):
    card_name = "Mental Note"

    def on_resolve(self, state):
        state.mill(2)
        state.draw(1)
        state.emit("Mental Note: mill 2, draw 1")
