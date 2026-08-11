"""Giant Tortoise — {1}{U} Creature — Turtle 1/1.
This creature gets +0/+3 as long as it's untapped.

A self-anthem via static_pt_bonus: +0/+3 to itself while it is untapped (a 1/4
that shrinks to 1/1 once it taps to attack)."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class GiantTortoise(Card):
    card_name = "Giant Tortoise"

    def static_pt_bonus(self, state, source, perm):
        if perm.uid == source.uid and not perm.tapped:
            return (0, 3)
        return (0, 0)
