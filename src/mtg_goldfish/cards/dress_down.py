"""Dress Down — {1}{U} Enchantment, flash. When it enters, draw a card.
Creatures lose all abilities (a global static not modelled in a goldfish).
At the beginning of the end step, sacrifice it."""
from .base import Card
from .registry import register


@register
class DressDown(Card):
    card_name = "Dress Down"

    def on_etb(self, state, permanent):
        state.draw(1)
        permanent.counters["end_step_sac"] = 1
        state.emit("Dress Down: draw a card (creatures-lose-abilities static not modelled)")
