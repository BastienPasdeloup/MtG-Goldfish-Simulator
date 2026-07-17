"""Mistrise Village — Land. Enters tapped unless you control a Mountain or a
Forest. {T}: Add {U}. Its "{U},{T}: your next spell can't be countered" ability
is irrelevant in a goldfish and is not modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import perm_has_subtype
from .base import Card
from .registry import register


@register
class MistriseVillage(Card):
    card_name = "Mistrise Village"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("U",))]

    def etb_tapped(self, state):
        return not any(p.is_land and perm_has_subtype(p, ("Mountain", "Forest"))
                       for p in state.battlefield)
