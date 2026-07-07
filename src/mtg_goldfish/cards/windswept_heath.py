"""Windswept Heath — Land. Fetch land; approximated as tapping for {W/G} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class WindsweptHeath(Card):
    card_name = 'Windswept Heath'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'G'))]
