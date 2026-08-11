"""Keldon Warlord — {2}{R}{R} Creature — Human Barbarian */*.
Keldon Warlord's power and toughness are each equal to the number of non-Wall
creatures you control.

Dynamic P/T counting your non-Wall creatures (including itself). It dies as a
state-based action if it's ever the only non-Wall creature and shrinks to 0 —
handled by the standard effective-toughness check."""
from __future__ import annotations

from .base import Card
from .registry import register


def _non_wall_creatures(state) -> int:
    return sum(1 for p in state.battlefield
               if p.is_creature_now and "wall" not in p.type_line.lower())


@register
class KeldonWarlord(Card):
    card_name = "Keldon Warlord"

    def dynamic_power(self, state, perm):
        return _non_wall_creatures(state)

    def dynamic_toughness(self, state, perm):
        return _non_wall_creatures(state)
