"""Green Ward — {W} Enchantment — Aura. Enchant creature.
Enchanted creature has protection from green.

Protection has no effect in a solitaire goldfish (no opposing green sources to be
protected from), so this is an Aura that simply attaches to one of your creatures
(one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class GreenWard(Card):
    card_name = "Green Ward"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}")
