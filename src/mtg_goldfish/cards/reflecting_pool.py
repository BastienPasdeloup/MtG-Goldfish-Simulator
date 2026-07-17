"""Reflecting Pool — Land. {T}: Add one mana of any type that a land you control
could produce. Approximated as one mana of any colour in the commander's colour
identity (the colours your mana base can make)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class ReflectingPool(Card):
    card_name = "Reflecting Pool"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state))]
