"""Hive of the Eye Tyrant — Land. Enters tapped if you control two or more other
lands. {T}: Add {B}.
{3}{B}: Becomes a 3/3 black Beholder creature with menace until end of turn
(still a land). Its attack trigger (exile a card from the DEFENDING player's
graveyard) has no effect against a phantom opponent, so it is not modelled."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import animate_land_action
from .base import Card
from .registry import register


@register
class HiveOfTheEyeTyrant(Card):
    card_name = "Hive of the Eye Tyrant"

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=("B",))]

    def etb_tapped(self, state):
        return sum(1 for p in state.battlefield if p.is_land) >= 2

    def battlefield_actions(self, state, perm):
        return animate_land_action(
            self, state, perm,
            cost=ManaCost(generic=3, pips=(("B", 1),)),
            type_line="Creature Land — Beholder",
            power=3, toughness=3, keywords=("menace",),
            label="Hive of the Eye Tyrant: become a 3/3 menacing Beholder",
        )
