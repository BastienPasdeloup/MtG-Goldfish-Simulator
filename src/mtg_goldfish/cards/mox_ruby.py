"""Mox Ruby — {0} Artifact. {T}: Add {R}.

A free mana rock: taps for one {R}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MoxRuby(Card):
    card_name = "Mox Ruby"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("R",))]
