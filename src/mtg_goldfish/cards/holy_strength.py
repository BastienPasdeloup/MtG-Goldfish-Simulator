"""Holy Strength — {W} Enchantment — Aura. Enchant creature.
Enchanted creature gets +1/+2.

Cast onto one of your creatures (one branch each); a static +1/+2 buff via
equip_mod."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class HolyStrength(Card):
    card_name = "Holy Strength"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}")

    def equip_mod(self, state, perm):
        return (1, 2)
