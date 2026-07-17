"""Fact or Fiction — {3}{U} Instant. Reveal the top five cards; an opponent
splits them into two piles, you take one to hand and the other to the graveyard.
With no opponent, the player takes the best two to hand (the rest to the
graveyard) — branching over which two."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class FactOrFiction(Card):
    card_name = "Fact or Fiction"

    def on_resolve(self, state):
        return dig_choose(state, 5, 2, rest="graveyard", source="Fact or Fiction")
