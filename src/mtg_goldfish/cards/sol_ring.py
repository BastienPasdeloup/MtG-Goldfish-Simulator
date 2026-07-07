"""Sol Ring — {1} artifact, taps for {C}{C}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class SolRing(Card):
    card_name = "Sol Ring"

    def mana_abilities(self, state) -> list[ManaAbility]:
        return [ManaAbility(amount=2, choices=("C",))]
