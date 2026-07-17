"""Sauron's Ransom — {1}{U}{B} Instant. An opponent splits the top four cards of
your library into two piles; you take one pile to hand and the other to the
graveyard. With no opponent, the player picks the best two to hand (the rest to
the graveyard). "The Ring tempts you" is not modelled."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class SauronsRansom(Card):
    card_name = "Sauron's Ransom"

    def on_resolve(self, state):
        return dig_choose(state, 4, 2, rest="graveyard", source="Sauron's Ransom")
