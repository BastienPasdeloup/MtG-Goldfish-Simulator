"""Exploration — {G} Enchantment.
You may play an additional land on each of your turns."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Exploration(Card):
    card_name = "Exploration"

    def extra_land_drops(self, state, perm):
        return 1
