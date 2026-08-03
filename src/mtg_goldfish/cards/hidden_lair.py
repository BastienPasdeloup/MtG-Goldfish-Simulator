"""Hidden Lair — Land. {T}: Add {C}. {T}: Add {U} or {B}. Activate the coloured
ability only if this land entered this turn or you control a basic land.
Approximation: the coloured mana is offered when you control a basic land (the
usual case in this deck); the "entered this turn" clause is not tracked per
permanent, so a turn-one tapland use without basics may under-offer {U}/{B}."""
from __future__ import annotations

from ..engine.mana import ManaAbility
from .base import Card
from .registry import register


@register
class HiddenLair(Card):
    card_name = "Hidden Lair"

    def mana_abilities_perm(self, state, perm):
        abilities = [ManaAbility(amount=1, choices=("C",))]
        if any(p.is_land and "basic" in p.type_line.lower() for p in state.battlefield):
            abilities.append(ManaAbility(amount=1, choices=("U", "B")))
        return abilities
