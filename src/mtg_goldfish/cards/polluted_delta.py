"""Polluted Delta — Land. Fetch land; approximated as tapping for {U/B} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class PollutedDelta(Card):
    card_name = 'Polluted Delta'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U', 'B'))]
