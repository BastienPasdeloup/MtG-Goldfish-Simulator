"""River of Tears — Land. {T}: Add {U}. If you played a land this turn, add {B}
instead."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class RiverOfTears(Card):
    card_name = "River of Tears"

    def mana_abilities(self, state):
        color = "B" if state.lands_played_this_turn > 0 else "U"
        return [ManaAbility(amount=1, choices=(color,))]
