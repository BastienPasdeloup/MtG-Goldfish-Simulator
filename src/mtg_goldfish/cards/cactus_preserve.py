"""Cactus Preserve — Land — Desert. Enters tapped. {T}: Add one mana of any type
a land you control could produce (approximated as the commander colour identity).
{3}: Until end of turn, becomes an X/X green Plant creature with reach, where X
is the greatest mana value among your commanders. It's still a land."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from ._common import animate_land_action, any_identity_color
from .base import Card
from .registry import register


def _commander_mv(state) -> int:
    cards = list(state.command_zone) + [p.card for p in state.battlefield
                                        if p.is_commander]
    return max((int(c.cmc) for c in cards), default=0)


@register
class CactusPreserve(Card):
    card_name = "Cactus Preserve"

    def etb_tapped(self, state):
        return True

    def mana_abilities(self, state):
        return [ManaAbility(amount=1, choices=any_identity_color(state))]

    def battlefield_actions(self, state, perm):
        x = _commander_mv(state)
        if x <= 0:
            return []
        return animate_land_action(
            self, state, perm,
            cost=ManaCost(generic=3),
            type_line="Creature Land — Plant Desert",
            power=x, toughness=x, keywords=("reach",),
            label=f"Cactus Preserve: become a {x}/{x} Plant")
