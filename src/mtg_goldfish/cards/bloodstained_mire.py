"""Bloodstained Mire — Land. Fetch land; approximated as tapping for {B/R} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class BloodstainedMire(Card):
    card_name = 'Bloodstained Mire'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('B', 'R'))]
