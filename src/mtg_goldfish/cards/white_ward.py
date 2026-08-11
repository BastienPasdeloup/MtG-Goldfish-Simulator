"""White Ward — {W} Enchantment — Aura. Enchant creature.
Enchanted creature has protection from white.

Protection has no effect in a solitaire goldfish, so this Aura simply attaches to
one of your creatures (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class WhiteWard(Card):
    card_name = "White Ward"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}")
