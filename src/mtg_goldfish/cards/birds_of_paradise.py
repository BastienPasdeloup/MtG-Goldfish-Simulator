"""Birds of Paradise — {G} Creature — Bird 0/1. Flying.
{T}: Add one mana of any color.

The classic mana dork: taps for one mana of any colour (the payment planner
respects summoning sickness on the turn it enters)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class BirdsOfParadise(Card):
    card_name = "Birds of Paradise"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("W", "U", "B", "R", "G"))]
