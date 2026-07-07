"""Scalding Tarn — Land. Fetch land; approximated as tapping for {U/R} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class ScaldingTarn(Card):
    card_name = 'Scalding Tarn'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U', 'R'))]
