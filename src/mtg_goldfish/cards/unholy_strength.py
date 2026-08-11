"""Unholy Strength — {B} Enchantment — Aura. Enchant creature.
Enchanted creature gets +2/+1.

Cast onto one of your creatures (one branch each); a static +2/+1 via equip_mod."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class UnholyStrength(Card):
    card_name = "Unholy Strength"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{B}")

    def equip_mod(self, state, perm):
        return (2, 1)
