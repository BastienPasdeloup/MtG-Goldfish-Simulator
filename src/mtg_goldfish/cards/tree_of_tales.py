"""Tree of Tales — Artifact Land. {T}: Add {G}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class TreeOfTales(Card):
    card_name = "Tree of Tales"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
