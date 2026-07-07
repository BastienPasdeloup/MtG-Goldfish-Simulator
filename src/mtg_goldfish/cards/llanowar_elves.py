"""Llanowar Elves — {G} creature, taps for {G} (subject to summoning sickness)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class LlanowarElves(Card):
    card_name = "Llanowar Elves"

    def mana_abilities(self, state) -> list[ManaAbility]:
        # The engine only offers a creature's tap ability once it can tap
        # (i.e. it has been under control since the start of the turn).
        return [ManaAbility(amount=1, choices=("G",))]
