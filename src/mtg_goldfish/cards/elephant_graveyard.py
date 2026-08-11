"""Elephant Graveyard — Land.
{T}: Add {C}.
{T}: Regenerate target Elephant.

Taps for {C}. The regenerate-an-Elephant ability is extremely niche (needs an
Elephant and shares the {T}); only the mana ability is offered."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class ElephantGraveyard(Card):
    card_name = "Elephant Graveyard"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
