"""Lure — {1}{G}{G} Enchantment — Aura. Enchant creature.
All creatures able to block enchanted creature do so.

The forced-block effect is inert with no opposing blockers, so this Aura simply
attaches to one of your creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Lure(Card):
    card_name = "Lure"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{G}{G}")
