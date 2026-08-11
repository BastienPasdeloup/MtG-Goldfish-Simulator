"""Mox Pearl — {0} Artifact. {T}: Add {W}.

A free mana rock: taps for one {W}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MoxPearl(Card):
    card_name = "Mox Pearl"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("W",))]
