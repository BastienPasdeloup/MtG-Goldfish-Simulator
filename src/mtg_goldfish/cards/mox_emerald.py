"""Mox Emerald — {0} Artifact. {T}: Add {G}.

A free mana rock: taps for one {G}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MoxEmerald(Card):
    card_name = "Mox Emerald"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
