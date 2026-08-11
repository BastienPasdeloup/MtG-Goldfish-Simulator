"""Burrowing — {R} Enchantment — Aura. Enchant creature.
Enchanted creature has mountainwalk.

Landwalk (unblockable vs a Mountain) is irrelevant with no blockers — the Aura
just attaches to one of your creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Burrowing(Card):
    card_name = "Burrowing"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{R}")
