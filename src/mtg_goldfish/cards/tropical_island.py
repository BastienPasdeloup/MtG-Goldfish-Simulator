"""Tropical Island — Land — Forest Island. Taps for {U/G}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class TropicalIsland(Card):
    card_name = 'Tropical Island'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U', 'G'))]
