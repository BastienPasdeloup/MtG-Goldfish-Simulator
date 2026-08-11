"""Fishliver Oil — {1}{U} Enchantment — Aura. Enchant creature.
Enchanted creature has islandwalk.

Islandwalk (evasion) is inert with no blockers, so this Aura simply attaches to one
of your creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class FishliverOil(Card):
    card_name = "Fishliver Oil"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{1}{U}")
