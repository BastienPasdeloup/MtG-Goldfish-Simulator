"""Crusade — {W}{W} Enchantment.
White creatures get +1/+1.

A global static anthem (static_pt_bonus) — every white creature you control gets
+1/+1 while Crusade is in play."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Crusade(Card):
    card_name = "Crusade"

    def static_pt_bonus(self, state, perm):
        if perm.is_creature_now and "W" in perm.colors:
            return (1, 1)
        return (0, 0)
