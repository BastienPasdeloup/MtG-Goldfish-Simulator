"""Aspect of Wolf — {1}{G} Enchantment — Aura. Enchant creature.
Enchanted creature gets +X/+Y, where X is half the number of Forests you control
(rounded down) and Y is half (rounded up).

Cast onto one of your creatures (one branch each); the buff is dynamic via
equip_mod, recomputed from your Forest count."""
from __future__ import annotations

from ._common import aura_enchant_actions, forest_count
from .base import Card
from .registry import register


@register
class AspectOfWolf(Card):
    card_name = "Aspect of Wolf"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{G}")

    def equip_mod(self, state, perm):
        f = forest_count(state)
        return (f // 2, (f + 1) // 2)
