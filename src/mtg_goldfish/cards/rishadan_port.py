"""Rishadan Port — Land.
{T}: Add {C}. "{1}, {T}: Tap target land" is opponent-facing — only the mana
ability is modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class RishadanPort(Card):
    card_name = "Rishadan Port"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
