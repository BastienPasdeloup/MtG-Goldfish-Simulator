"""Island — basic land, taps for {U}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Island(Card):
    card_name = "Island"

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=("U",))]
