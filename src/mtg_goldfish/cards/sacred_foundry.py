"""Sacred Foundry — Land — Mountain Plains. Taps for {W/R}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class SacredFoundry(Card):
    card_name = 'Sacred Foundry'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'R'))]
