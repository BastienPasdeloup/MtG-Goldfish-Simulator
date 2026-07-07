"""Volcanic Island — Land — Island Mountain. Taps for {U/R}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class VolcanicIsland(Card):
    card_name = 'Volcanic Island'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U', 'R'))]
