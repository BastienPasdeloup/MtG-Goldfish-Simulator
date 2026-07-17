"""Thought Scour — {U} Instant. Target player mills two cards; draw a card.
(You mill yourself — filling the graveyard for delve/escape.)"""
from .base import Card
from .registry import register


@register
class ThoughtScour(Card):
    card_name = "Thought Scour"

    def on_resolve(self, state):
        state.mill(2)
        state.draw(1)
        state.emit("Thought Scour: mill 2, draw 1")
