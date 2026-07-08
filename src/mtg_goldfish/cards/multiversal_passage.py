"""Multiversal Passage — Land. As it enters, choose a basic land type; then you
may pay 2 life, otherwise it enters tapped. It is the chosen type (branches:
5 types × {pay 2 life untapped, tapped})."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import BASIC_TYPES, TYPE_COLOR
from .base import Card
from .registry import register


@register
class MultiversalPassage(Card):
    card_name = "Multiversal Passage"

    def etb_modes(self, state):
        modes = []
        for t in BASIC_TYPES:
            if state.life > 2:
                modes.append({"label": f"{t}, pay 2 life, untapped",
                              "tapped": False, "life": 2, "choice": t})
            modes.append({"label": f"{t}, tapped", "tapped": True, "life": 0, "choice": t})
        return modes

    def mana_abilities_perm(self, state, perm):
        color = TYPE_COLOR.get(perm.chosen or "", "C")
        return [ManaAbility(amount=1, choices=(color,))]
