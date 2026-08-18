"""Mishra's Workshop — Land.
{T}: Add {C}{C}{C}. Spend this mana only to cast artifact spells.

Produces three artifact-only colourless (restriction "A"): the engine's mana
subsystem lets this mana pay only when casting an artifact spell, never for
nonartifact spells or activated abilities."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class MishrasWorkshop(Card):
    card_name = "Mishra's Workshop"
    produced_mana_restrictions = frozenset({"A"})

    def mana_abilities(self, state):
        return [ManaAbility(amount=3, choices=("C",), restriction="A")]
