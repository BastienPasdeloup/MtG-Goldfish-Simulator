"""Underground Sea — Land — Island Swamp. Taps for {U/B}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class UndergroundSea(Card):
    card_name = 'Underground Sea'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U', 'B'))]
