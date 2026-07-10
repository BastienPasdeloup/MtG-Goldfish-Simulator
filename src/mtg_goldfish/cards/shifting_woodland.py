"""Shifting Woodland — Land.
Enters tapped unless you control a Forest. {T}: Add {G}.
Approximation: the delirium copy-a-permanent-from-graveyard ability is not
modelled (until-end-of-turn copies are out of scope)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import controls_forest
from .base import Card
from .registry import register


@register
class ShiftingWoodland(Card):
    card_name = "Shifting Woodland"

    def etb_tapped(self, state):
        return not controls_forest(state)

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
