"""Stock Up — {2}{U} Sorcery. Look at the top five cards; put two into your hand
and the rest on the bottom in any order."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class StockUp(Card):
    card_name = "Stock Up"

    def on_resolve(self, state):
        return dig_choose(state, 5, 2, rest="bottom", source="Stock Up")
