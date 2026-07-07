"""Concealed Courtyard — Land. Taps for {W/B}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class ConcealedCourtyard(Card):
    card_name = 'Concealed Courtyard'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'B'))]
