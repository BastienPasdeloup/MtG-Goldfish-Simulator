"""Arid Mesa — Land. Fetch land; approximated as tapping for {W/R} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class AridMesa(Card):
    card_name = 'Arid Mesa'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'R'))]
