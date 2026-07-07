"""Temple Garden — Land — Forest Plains. Taps for {W/G}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class TempleGarden(Card):
    card_name = 'Temple Garden'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'G'))]
