"""Weakness — {B} Enchantment — Aura. Enchant creature.
Enchanted creature gets -2/-1.

A debuff meant for an opponent's creature; on one of your own it is a downside, so
the search won't cast it, but it is a real -2/-1 via equip_mod (one branch per your
creature)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class Weakness(Card):
    card_name = "Weakness"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{B}")

    def equip_mod(self, state, perm):
        return (-2, -1)
