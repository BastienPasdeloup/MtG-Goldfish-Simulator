"""Rakshasa's Bargain — {2/B}{2/G}{2/U} Instant. Look at the top four cards; put
two into your hand and the rest into your graveyard."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class RakshasasBargain(Card):
    card_name = "Rakshasa's Bargain"

    def on_resolve(self, state):
        return dig_choose(state, 4, 2, rest="graveyard", source="Rakshasa's Bargain")
