"""Seachrome Coast — Land. Taps for {W/U}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class SeachromeCoast(Card):
    card_name = 'Seachrome Coast'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U'))]
