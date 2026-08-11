"""Mox Jet — {0} Artifact. {T}: Add {B}.

A free mana rock: taps for one {B}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MoxJet(Card):
    card_name = "Mox Jet"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]
