"""Mountain — basic land, taps for {R}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class Mountain(Card):
    card_name = "Mountain"

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=1, choices=("R",))]
