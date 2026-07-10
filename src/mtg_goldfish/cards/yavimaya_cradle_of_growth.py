"""Yavimaya, Cradle of Growth — Legendary Land.
"Each land is a Forest": Yavimaya itself taps for {G}, and every
'do you control a Forest?' check in this deck (Castle Garenbrig, Shifting
Woodland, Gingerbread Cabin — via `_common.controls_forest`/`forest_count`)
honours it. Approximation: OTHER lands don't gain '{T}: Add {G}' (the deck is
green-heavy already, so this rarely matters)."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class YavimayaCradleOfGrowth(Card):
    card_name = "Yavimaya, Cradle of Growth"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]
