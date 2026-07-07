"""Marsh Flats — Land. Fetch land; approximated as tapping for {W/B} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MarshFlats(Card):
    card_name = 'Marsh Flats'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'B'))]
