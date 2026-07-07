"""Plains — basic land, taps for {W}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Plains(Card):
    card_name = "Plains"

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=("W",))]
