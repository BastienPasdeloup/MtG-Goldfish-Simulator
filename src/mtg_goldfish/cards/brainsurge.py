"""Brainsurge — {2}{U} Instant. Draw four cards, then put two cards from your
hand on top of your library in any order.

Net +2 cards, but on an ordered library the choice of WHICH two to keep (and
which two to leave on top to draw next) matters — a needed piece can sit at
depth 3-4. Modelled as "look at the top four, keep two in hand, put two back on
top" (`dig_choose`), which is the equivalent reachable configuration and lets
the search branch over the keep choice instead of only ever seeing the top two."""
from ._common import dig_choose
from .base import Card
from .registry import register


@register
class Brainsurge(Card):
    card_name = "Brainsurge"

    def on_resolve(self, state):
        return dig_choose(state, look_n=4, keep_n=2, rest="top",
                          source="Brainsurge", to_hand=True)
