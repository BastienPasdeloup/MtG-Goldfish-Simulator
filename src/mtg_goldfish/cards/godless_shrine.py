"""Godless Shrine — Land — Plains Swamp. Taps for {W/B}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class GodlessShrine(Card):
    card_name = 'Godless Shrine'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'B'))]
