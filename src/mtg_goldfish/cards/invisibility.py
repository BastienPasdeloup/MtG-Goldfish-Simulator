"""Invisibility — {U}{U} Enchantment — Aura. Enchant creature.
Enchanted creature can't be blocked except by Walls.

Evasion has no effect with no blockers, so this Aura simply attaches to one of
your creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Invisibility(Card):
    card_name = "Invisibility"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{U}{U}")
