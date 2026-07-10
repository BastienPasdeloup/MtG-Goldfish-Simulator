"""Ghost Quarter — Land.
{T}: Add {C}. The destroy-a-land ability is opponent-facing (blowing up your
own land to fetch a basic is strictly worse than Prismatic Vista here) — only
the mana ability is modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class GhostQuarter(Card):
    card_name = "Ghost Quarter"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
