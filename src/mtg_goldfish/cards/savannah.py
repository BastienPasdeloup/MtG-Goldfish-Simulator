"""Savannah — Land — Forest Plains. Taps for {W/G}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Savannah(Card):
    card_name = 'Savannah'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'G'))]
