"""Floodfarm Verge — Land. {T}: Add {W}. {T}: Add {U} only if you control a
Plains or an Island."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import perm_has_subtype
from .base import Card
from .registry import register


@register
class FloodfarmVerge(Card):
    card_name = "Floodfarm Verge"

    def mana_abilities_perm(self, state, perm):
        unlocked = any(
            p.uid != perm.uid and perm_has_subtype(p, ("Plains", "Island"))
            for p in state.battlefield
        )
        if unlocked:
            return [ManaAbility(amount=1, choices=("W", "U"))]
        return [ManaAbility(amount=1, choices=("W",))]
