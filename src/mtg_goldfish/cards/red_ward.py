"""Red Ward — {W} Enchantment — Aura. Enchant creature.
Enchanted creature has protection from red.

Protection has no effect in a solitaire goldfish (no opposing red sources), so
this Aura simply attaches to one of your creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class RedWard(Card):
    card_name = "Red Ward"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}")
