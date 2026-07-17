"""Preordain — {U} Sorcery. Scry 2, then draw a card. Modelled as taking one of
the top three cards into your hand, the rest to the bottom (scry + draw)."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class Preordain(Card):
    card_name = "Preordain"

    def on_resolve(self, state):
        return dig_choose(state, 3, 1, rest="bottom", source="Preordain")
