"""Raucous Theater — Land — Swamp Mountain. Enters tapped; {T}: Add {B} or {R};
ETB: surveil 1."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import surveil_branches
from .base import Card
from .registry import register


@register
class RaucousTheater(Card):
    card_name = "Raucous Theater"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B", "R"))]

    def etb_tapped(self, state):
        return True

    def on_etb(self, state, permanent):
        return surveil_branches(state, 1, "Raucous Theater")
