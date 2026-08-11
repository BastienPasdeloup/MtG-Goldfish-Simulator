"""Consecrate Land — {W} Enchantment — Aura. Enchant land.
Enchanted land has indestructible and can't be enchanted by other Auras.

Indestructible is a no-op with no destruction in a goldfish — the Aura just
attaches to one of your lands (one branch each)."""
from __future__ import annotations

from ._common import aura_enchant_actions
from .base import Card
from .registry import register


@register
class ConsecrateLand(Card):
    card_name = "Consecrate Land"

    def cast_actions(self, state):
        return aura_enchant_actions(self, state, cost="{W}", pred=lambda p: p.is_land)
