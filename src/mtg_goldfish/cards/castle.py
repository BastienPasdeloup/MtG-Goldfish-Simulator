"""Castle — {3}{W} Enchantment.
Untapped creatures you control get +0/+2.

A conditional static anthem (static_pt_bonus): every UNTAPPED creature gets
+0/+2 while Castle is in play."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Castle(Card):
    card_name = "Castle"

    def static_pt_bonus(self, state, source, perm):
        if perm.is_creature_now and not perm.tapped:
            return (0, 2)
        return (0, 0)
