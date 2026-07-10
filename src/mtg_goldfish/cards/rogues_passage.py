"""Rogue's Passage — Land.
{T}: Add {C}. The unblockable ability is meaningless in a goldfish (there are
no blockers) — only the mana ability is modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class RoguesPassage(Card):
    card_name = "Rogue's Passage"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
