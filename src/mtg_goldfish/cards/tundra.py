"""Tundra — Land — Plains Island. Taps for {W/U}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Tundra(Card):
    card_name = 'Tundra'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U'))]
