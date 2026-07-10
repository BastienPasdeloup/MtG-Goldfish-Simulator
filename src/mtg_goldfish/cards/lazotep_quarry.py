"""Lazotep Quarry — Land — Desert.
{T}: Add {C}. Approximations: the sacrifice-a-creature mana ability and the
Zombie-reanimation mode are not modelled (sacrificing real creatures for one
mana is almost never right, and no creature in this deck wants the 4/4 Zombie
treatment)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class LazotepQuarry(Card):
    card_name = "Lazotep Quarry"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]
