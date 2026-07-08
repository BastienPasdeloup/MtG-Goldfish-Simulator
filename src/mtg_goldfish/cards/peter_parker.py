"""Peter Parker // Amazing Spider-Man — {1}{W} Legendary 0/1.
ETB: create a 2/1 green Spider creature token with reach.
{1}{G}{W}{U}: transform (sorcery). The back face's web-slinging alternative
cost for legendary spells is not modelled — documented approximation."""
from __future__ import annotations

from ..engine.mana import ManaCost
from ._common import transform_actions
from .base import Card
from .registry import register


@register
class PeterParker(Card):
    card_name = "Peter Parker // Amazing Spider-Man"

    def on_etb(self, state, permanent):
        state.make_token("Spider", 2, 1, "Token Creature — Spider")
        return None

    def battlefield_actions(self, state, perm):
        return transform_actions(
            state, perm,
            ManaCost(generic=1, pips=(("G", 1), ("W", 1), ("U", 1))),
            "Amazing Spider-Man",
        )
