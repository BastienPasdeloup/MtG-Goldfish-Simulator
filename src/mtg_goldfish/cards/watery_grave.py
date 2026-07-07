"""Watery Grave — Land — Island Swamp. Taps for {U/B}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class WateryGrave(Card):
    card_name = 'Watery Grave'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U', 'B'))]
