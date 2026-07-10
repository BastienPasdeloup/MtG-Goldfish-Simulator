"""Dust Bowl — Land.
{T}: Add {C}. The Strip-Mine ability ({3}, {T}, Sac a land: destroy target
nonbasic land) only targets opponents' lands in practice — no use in a
solitaire game, so only the mana ability is modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class DustBowl(Card):
    card_name = "Dust Bowl"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
