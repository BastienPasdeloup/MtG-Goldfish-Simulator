"""Brainsurge — {2}{U} Instant. Draw four cards, then put two cards from your
hand on top of your library. Modelled as a net draw of two cards."""
from .base import Card
from .registry import register


@register
class Brainsurge(Card):
    card_name = "Brainsurge"

    def on_resolve(self, state):
        state.draw(2)
        state.emit("Brainsurge: net draw two cards (put-back of 2 not modelled)")
