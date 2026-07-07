"""Taiga — Land — Mountain Forest. Taps for {R/G}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Taiga(Card):
    card_name = 'Taiga'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('R', 'G'))]
