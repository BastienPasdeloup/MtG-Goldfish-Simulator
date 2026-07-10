"""Crumbling Vestige — Land.
Enters tapped. ETB: add one mana of any color (identity — goes to the pool,
usable this phase). {T}: Add {C}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import any_identity_color
from .base import Card
from .registry import register


@register
class CrumblingVestige(Card):
    card_name = "Crumbling Vestige"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def on_etb(self, state, permanent):
        color = any_identity_color(state)[0]
        state.mana_pool.add(color, 1)
        state.emit(f"Crumbling Vestige: add {{{color}}}")
