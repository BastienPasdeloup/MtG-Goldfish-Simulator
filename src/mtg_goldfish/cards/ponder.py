"""Ponder — {U} Sorcery. Look at the top three cards, rearrange them, then draw a
card. Modelled as putting one of the top three into your hand (the rest stay on
top); the "may shuffle" reset is omitted."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class Ponder(Card):
    card_name = "Ponder"

    def on_resolve(self, state):
        return dig_choose(state, 3, 1, rest="top", source="Ponder")
