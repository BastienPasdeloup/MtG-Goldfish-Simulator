"""Mishra's Factory — Land. {T}: Add {C}.
{1}: Becomes a 2/2 Assembly-Worker artifact creature until end of turn (still a
land). Its '{T}: target Assembly-Worker gets +1/+1' pump is marginal in a
solitaire goldfish and is not modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import animate_land_action
from .base import Card
from .registry import register


@register
class MishrasFactory(Card):
    card_name = "Mishra's Factory"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("C",))]

    def battlefield_actions(self, state, perm):
        return animate_land_action(
            self, state, perm,
            cost=ManaCost(generic=1),
            type_line="Artifact Creature Land — Assembly-Worker",
            power=2, toughness=2,
            label="Mishra's Factory: become a 2/2 Assembly-Worker",
        )
