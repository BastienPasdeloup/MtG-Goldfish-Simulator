"""Bayou — Land — Swamp Forest. Taps for {B/G}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Bayou(Card):
    card_name = 'Bayou'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('B', 'G'))]
