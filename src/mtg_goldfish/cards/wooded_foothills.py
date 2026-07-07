"""Wooded Foothills — Land. Fetch land; approximated as tapping for {R/G} (the colours of the land types it can fetch).
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class WoodedFoothills(Card):
    card_name = 'Wooded Foothills'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('R', 'G'))]
