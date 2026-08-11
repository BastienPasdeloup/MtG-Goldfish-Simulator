"""Mox Sapphire — {0} Artifact. {T}: Add {U}.

A free mana rock: taps for one {U}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MoxSapphire(Card):
    card_name = "Mox Sapphire"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]
