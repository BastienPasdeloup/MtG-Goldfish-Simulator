"""Flooded Strand — Land. Fetch land; approximated as tapping for {W/U} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class FloodedStrand(Card):
    card_name = 'Flooded Strand'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U'))]
