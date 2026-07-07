"""City of Brass — Land. Taps for {W/U/B/R/G}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class CityOfBrass(Card):
    card_name = 'City of Brass'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U', 'B', 'R', 'G'))]
