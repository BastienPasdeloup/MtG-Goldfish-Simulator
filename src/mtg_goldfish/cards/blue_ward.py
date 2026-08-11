"""Blue Ward — {W} Enchantment — Aura. Enchant creature.
Enchanted creature has protection from blue.

Protection has no effect in a solitaire goldfish (no opposing blue sources to
be protected from), so this is an Aura that simply attaches to one of your
creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class BlueWard(Card):
    card_name = "Blue Ward"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}")
