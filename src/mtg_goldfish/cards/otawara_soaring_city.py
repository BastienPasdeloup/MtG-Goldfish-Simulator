"""Otawara, Soaring City — Legendary Land. Taps for {U}.
"""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class OtawaraSoaringCity(Card):
    card_name = 'Otawara, Soaring City'

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=('U',))]
