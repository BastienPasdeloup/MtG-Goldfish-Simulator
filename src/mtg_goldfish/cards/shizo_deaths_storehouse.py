"""Shizo, Death's Storehouse — Legendary Land. {T}: Add {B}.
Its '{B}, {T}: target legendary creature gains fear' ability is a no-op in a
goldfish (there are no blockers to evade), so only the mana ability is modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class ShizoDeathsStorehouse(Card):
    card_name = "Shizo, Death's Storehouse"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]
