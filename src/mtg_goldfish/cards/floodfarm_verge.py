"""Floodfarm Verge — Land. Taps for {W/U}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class FloodfarmVerge(Card):
    card_name = 'Floodfarm Verge'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U'))]
