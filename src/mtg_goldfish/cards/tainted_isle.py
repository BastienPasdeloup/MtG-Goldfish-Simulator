"""Tainted Isle — Land. {T}: Add {C}. {T}: Add {U} or {B}. Activate the
coloured ability only if you control a Swamp."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from ._common import perm_has_subtype
from .base import Card
from .registry import register


@register
class TaintedIsle(Card):
    card_name = "Tainted Isle"

    def mana_abilities_perm(self, state, perm):
        abilities = [ManaAbility(amount=1, choices=("C",))]
        if any(p.is_land and perm_has_subtype(p, ("Swamp",)) for p in state.battlefield):
            abilities.append(ManaAbility(amount=1, choices=("U", "B")))
        return abilities
