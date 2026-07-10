"""Mirrorpool — Land.
Enters tapped. {T}: Add {C}. Approximation: the copy-spell and copy-creature
abilities are not modelled (copying is out of scope for the engine)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Mirrorpool(Card):
    card_name = "Mirrorpool"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
