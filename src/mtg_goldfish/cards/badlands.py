"""Badlands — Land — Swamp Mountain. Taps for {B/R}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Badlands(Card):
    card_name = 'Badlands'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('B', 'R'))]
