"""Pit of Offerings — Land — Cave.
Enters tapped. {T}: Add {C}. Approximations: exiling cards from graveyards is
skipped (self-milling is this deck's engine — exiling own cards is a
downside), so the "any exiled color" ability never applies."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class PitOfOfferings(Card):
    card_name = "Pit of Offerings"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
