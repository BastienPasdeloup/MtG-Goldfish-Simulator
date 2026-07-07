"""Starting Town — Land — Town. Taps for {W/U/B/R/G/C}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class StartingTown(Card):
    card_name = 'Starting Town'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('W', 'U', 'B', 'R', 'G', 'C'))]
