"""Gingerbread Cabin — Land — Forest.
({T}: Add {G}.) Enters tapped unless you control three or more other Forests.
When it enters untapped, create a Food token."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import forest_count
from .base import Card
from .registry import register


@register
class GingerbreadCabin(Card):
    card_name = "Gingerbread Cabin"

    def etb_tapped(self, state):
        return forest_count(state) < 3

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("G",))]

    def on_etb(self, state, permanent):
        if not permanent.tapped:
            state.make_token("Food", 0, 0, "Token Artifact — Food")
            state.emit("Gingerbread Cabin entered untapped — Food token")
