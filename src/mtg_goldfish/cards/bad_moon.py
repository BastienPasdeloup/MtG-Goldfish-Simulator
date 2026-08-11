"""Bad Moon — {1}{B} Enchantment.
Black creatures get +1/+1.

A global static anthem (via static_pt_bonus): every black creature on the
battlefield gets +1/+1 while Bad Moon is in play."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class BadMoon(Card):
    card_name = "Bad Moon"

    def static_pt_bonus(self, state, source, perm):
        if perm.is_creature_now and "B" in perm.colors:
            return (1, 1)
        return (0, 0)
